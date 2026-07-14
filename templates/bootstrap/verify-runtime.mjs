#!/usr/bin/env node
import { createHash } from "node:crypto";
import { constants as fsConstants, createReadStream, createWriteStream } from "node:fs";
import {
    chmod,
    lstat,
    mkdir,
    mkdtemp,
    open,
    readFile,
    readdir,
    readlink,
    realpath,
    rename,
    rm,
    stat,
    symlink,
    link as hardlink,
    writeFile,
} from "node:fs/promises";
import { request } from "node:https";
import { dirname, isAbsolute, join, posix, relative, resolve, sep } from "node:path";
import { spawn } from "node:child_process";
import { gunzipSync, inflateRawSync } from "node:zlib";

const PRODUCTION_LIMITS = Object.freeze({
    max_compressed_bytes: 268435456,
    max_expanded_bytes: 1073741824,
    max_member_bytes: 268435456,
    max_members: 100000,
    max_redirects: 3,
    max_path_bytes: 4096,
});
const MAX_JSON_BYTES = 1048576;
const MAX_LINK_DEPTH = 8;
const EXPECTED_TARGETS = Object.freeze([
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
]);
const EXPECTED_RUNTIME_PREFIX = "https://github.com/astral-sh/python-build-standalone/releases/download/20260510/";
const VERSION_PATTERN = /^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/u;
const HEX_256 = /^[0-9a-f]{64}$/u;
const HEX_512 = /^[0-9a-f]{128}$/u;
const HOST_PATTERN = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/u;

class BootstrapError extends Error {}

function fail(message) {
    throw new BootstrapError(message);
}

class DuplicateSafeJsonParser {
    constructor(text) {
        this.text = text;
        this.offset = 0;
    }

    parse() {
        const value = this.value(0);
        this.space();
        if (this.offset !== this.text.length) {
            fail("JSON has trailing data");
        }
        return value;
    }

    space() {
        while (/[\t\n\r ]/u.test(this.text[this.offset] ?? "")) {
            this.offset += 1;
        }
    }

    value(depth) {
        if (depth > 32) {
            fail("JSON nesting exceeds limit");
        }
        this.space();
        const token = this.text[this.offset];
        if (token === "{") {
            return this.object(depth + 1);
        }
        if (token === "[") {
            return this.array(depth + 1);
        }
        if (token === "\"") {
            return this.string();
        }
        for (const [literal, value] of [["true", true], ["false", false], ["null", null]]) {
            if (this.text.startsWith(literal, this.offset)) {
                this.offset += literal.length;
                return value;
            }
        }
        const match = this.text.slice(this.offset).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/u);
        if (match !== null) {
            this.offset += match[0].length;
            const value = Number(match[0]);
            if (!Number.isSafeInteger(value)) {
                fail("JSON numbers must be safe integers");
            }
            return value;
        }
        fail("JSON syntax is invalid");
    }

    object(depth) {
        this.offset += 1;
        const result = Object.create(null);
        const keys = new Set();
        this.space();
        if (this.text[this.offset] === "}") {
            this.offset += 1;
            return result;
        }
        while (true) {
            this.space();
            if (this.text[this.offset] !== "\"") {
                fail("JSON object key is invalid");
            }
            const key = this.string();
            if (keys.has(key)) {
                fail(`duplicate JSON key: ${key}`);
            }
            keys.add(key);
            this.space();
            if (this.text[this.offset] !== ":") {
                fail("JSON object separator is invalid");
            }
            this.offset += 1;
            result[key] = this.value(depth);
            this.space();
            const delimiter = this.text[this.offset++];
            if (delimiter === "}") {
                return result;
            }
            if (delimiter !== ",") {
                fail("JSON object delimiter is invalid");
            }
        }
    }

    array(depth) {
        this.offset += 1;
        const result = [];
        this.space();
        if (this.text[this.offset] === "]") {
            this.offset += 1;
            return result;
        }
        while (true) {
            result.push(this.value(depth));
            this.space();
            const delimiter = this.text[this.offset++];
            if (delimiter === "]") {
                return result;
            }
            if (delimiter !== ",") {
                fail("JSON array delimiter is invalid");
            }
        }
    }

    string() {
        const start = this.offset;
        this.offset += 1;
        let escaped = false;
        while (this.offset < this.text.length) {
            const code = this.text.charCodeAt(this.offset);
            if (code < 0x20) {
                fail("JSON string contains a control character");
            }
            if (!escaped && code === 0x22) {
                this.offset += 1;
                try {
                    return JSON.parse(this.text.slice(start, this.offset));
                } catch {
                    fail("JSON string escape is invalid");
                }
            }
            if (!escaped && code === 0x5c) {
                escaped = true;
            } else {
                escaped = false;
            }
            this.offset += 1;
        }
        fail("JSON string is unterminated");
    }
}

function parseJsonBytes(payload, label) {
    if (payload.length > MAX_JSON_BYTES) {
        fail(`${label} exceeds the JSON size limit`);
    }
    let text;
    try {
        text = new TextDecoder("utf-8", { fatal: true }).decode(payload);
    } catch {
        fail(`${label} is not valid UTF-8`);
    }
    return new DuplicateSafeJsonParser(text).parse();
}

function exactObject(value, label, fields) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        fail(`${label} must be an object`);
    }
    const actual = Object.keys(value);
    for (const field of fields) {
        if (!actual.includes(field)) {
            fail(`${label} missing required field: ${field}`);
        }
    }
    for (const field of actual) {
        if (!fields.includes(field)) {
            fail(`${label} has unknown field: ${field}`);
        }
    }
    return value;
}

function stringField(value, label, pattern = null) {
    if (typeof value !== "string" || value.length === 0 || (pattern !== null && !pattern.test(value))) {
        fail(`${label} is invalid`);
    }
    return value;
}

function httpsUrl(value, label) {
    const text = stringField(value, label);
    let parsed;
    try {
        parsed = new URL(text);
    } catch {
        fail(`${label} is not a valid URL`);
    }
    if (parsed.protocol !== "https:" || parsed.username !== "" || parsed.password !== "" || parsed.hash !== "") {
        fail(`${label} must use HTTPS without credentials or fragments`);
    }
    return parsed;
}

function validateIdentity(value, label) {
    const identity = exactObject(value, label, ["bundled_plugins", "compatibility_provider_version", "core_version", "schema_version"]);
    if (!Number.isInteger(identity.schema_version) || identity.schema_version < 1 || identity.schema_version > 2) {
        fail(`${label}.schema_version is not supported by bootstrap protocol v1`);
    }
    stringField(identity.core_version, `${label}.core_version`, VERSION_PATTERN);
    stringField(identity.compatibility_provider_version, `${label}.compatibility_provider_version`, VERSION_PATTERN);
    const plugins = exactObject(identity.bundled_plugins, `${label}.bundled_plugins`, Object.keys(identity.bundled_plugins));
    for (const [name, version] of Object.entries(plugins)) {
        stringField(name, "plugin name");
        stringField(version, `plugin ${name}`, VERSION_PATTERN);
    }
    return identity;
}

function validateLock(document) {
    const lock = exactObject(document, "consumer runtime lock", ["schema_version", "package", "zipapp", "runtimes", "acquisition"]);
    if (lock.schema_version !== 1) {
        fail("schema_version must be 1");
    }
    const packageIdentity = exactObject(lock.package, "package", ["name", "version", "registry_url", "tarball_url", "registry_sri", "sha512", "allowed_mirror_url"]);
    if (packageIdentity.name !== "agentharness-toolkit") {
        fail("package.name is not supported");
    }
    stringField(packageIdentity.version, "package.version", VERSION_PATTERN);
    const registry = httpsUrl(packageIdentity.registry_url, "package.registry_url");
    if (registry.href !== "https://registry.npmjs.org/") {
        fail("package.registry_url is not canonical");
    }
    const tarball = httpsUrl(packageIdentity.tarball_url, "package.tarball_url");
    if (tarball.href !== `https://registry.npmjs.org/agentharness-toolkit/-/agentharness-toolkit-${packageIdentity.version}.tgz`) {
        fail("package.tarball_url is not canonical for its identity");
    }
    httpsUrl(packageIdentity.allowed_mirror_url, "package.allowed_mirror_url");
    stringField(packageIdentity.sha512, "package.sha512", HEX_512);
    if (!/^sha512-[A-Za-z0-9+/]+={0,2}$/u.test(packageIdentity.registry_sri)) {
        fail("package.registry_sri is invalid");
    }
    const sri = Buffer.from(packageIdentity.registry_sri.slice(7), "base64");
    if (sri.length !== 64 || sri.toString("hex") !== packageIdentity.sha512) {
        fail("package registry digest identities disagree");
    }
    const zipapp = exactObject(lock.zipapp, "zipapp", ["path", "sha512", "core_version", "schema_version", "bundled_plugins", "compatibility_provider_version"]);
    if (zipapp.path !== "package/dist/agentharness.pyz") {
        fail("zipapp.path is not supported");
    }
    stringField(zipapp.sha512, "zipapp.sha512", HEX_512);
    validateIdentity({
        bundled_plugins: zipapp.bundled_plugins,
        compatibility_provider_version: zipapp.compatibility_provider_version,
        core_version: zipapp.core_version,
        schema_version: zipapp.schema_version,
    }, "zipapp identity");
    if (!Array.isArray(lock.runtimes) || lock.runtimes.length !== 4) {
        fail("runtimes must contain exactly four entries");
    }
    const targetSet = new Set();
    for (const runtime of lock.runtimes) {
        exactObject(runtime, "runtime", ["target", "url", "sha256", "sha512", "archive_prefix", "interpreter_path"]);
        if (!EXPECTED_TARGETS.includes(runtime.target) || targetSet.has(runtime.target)) {
            fail("runtime target inventory is invalid");
        }
        targetSet.add(runtime.target);
        const filename = `cpython-3.12.13%2B20260510-${runtime.target}-install_only_stripped.tar.gz`;
        if (httpsUrl(runtime.url, "runtime.url").href !== EXPECTED_RUNTIME_PREFIX + filename) {
            fail("runtime URL identity is invalid");
        }
        stringField(runtime.sha256, "runtime.sha256", HEX_256);
        stringField(runtime.sha512, "runtime.sha512", HEX_512);
        if (runtime.archive_prefix !== "python/" || runtime.interpreter_path !== "python/bin/python3") {
            fail("runtime layout identity is invalid");
        }
    }
    if (!EXPECTED_TARGETS.every(target => targetSet.has(target))) {
        fail("runtime target inventory is incomplete");
    }
    const acquisition = exactObject(lock.acquisition, "acquisition", ["selected_target", "selected_source", "mirror_policy", "limits", "bootstrap_protocol_version"]);
    if (!EXPECTED_TARGETS.includes(acquisition.selected_target) || !["upstream", "mirror"].includes(acquisition.selected_source) || acquisition.bootstrap_protocol_version !== 1) {
        fail("acquisition identity is invalid");
    }
    const mirror = exactObject(acquisition.mirror_policy, "mirror_policy", ["require_https", "require_matching_digest", "allowed_runtime_mirror_hosts"]);
    if (mirror.require_https !== true || mirror.require_matching_digest !== true || !Array.isArray(mirror.allowed_runtime_mirror_hosts)) {
        fail("mirror policy is invalid");
    }
    const mirrorHosts = new Set();
    for (const host of mirror.allowed_runtime_mirror_hosts) {
        stringField(host, "runtime mirror host", HOST_PATTERN);
        if (mirrorHosts.has(host)) {
            fail("runtime mirror host is duplicate");
        }
        mirrorHosts.add(host);
    }
    const limits = exactObject(acquisition.limits, "limits", Object.keys(PRODUCTION_LIMITS));
    for (const [key, value] of Object.entries(PRODUCTION_LIMITS)) {
        if (limits[key] !== value) {
            fail(`lock ${key} does not match protocol v1`);
        }
    }
    if (acquisition.selected_source === "mirror") {
        fail("runtime mirror selection requires the v2 acquisition protocol");
    }
    return lock;
}

function selectedRuntime(lock) {
    const platform = process.platform === "linux" ? "unknown-linux-gnu" : process.platform === "darwin" ? "apple-darwin" : null;
    const architecture = process.arch === "x64" ? "x86_64" : process.arch === "arm64" ? "aarch64" : null;
    if (platform === null || architecture === null) {
        fail("this operating-system target is not supported");
    }
    const detected = `${architecture}-${platform}`;
    if (lock.acquisition.selected_target !== detected && process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE !== "1") {
        fail("lock selected target does not match this host");
    }
    return lock.runtimes.find(runtime => runtime.target === lock.acquisition.selected_target);
}

async function digestFile(path, algorithm) {
    const digest = createHash(algorithm);
    const stream = createReadStream(path);
    for await (const chunk of stream) {
        digest.update(chunk);
    }
    return digest.digest("hex");
}

async function readAuthenticatedArchive(path, expected, label, requireCacheMetadata = false) {
    let handle;
    try {
        handle = await open(path, fsConstants.O_RDONLY | fsConstants.O_NOFOLLOW);
    } catch (error) {
        if (error?.code === "ELOOP") {
            fail(`${label} must be a cache-owned regular file`);
        }
        throw error;
    }
    try {
        const file = await handle.stat();
        const ownedByProcess = typeof process.getuid !== "function" || file.uid === process.getuid();
        if (!file.isFile()) {
            fail(`${label} must be a regular file`);
        }
        if (requireCacheMetadata && (!ownedByProcess || file.nlink !== 1 || (file.mode & 0o777) !== 0o600)) {
            fail(`${label} must be a cache-owned regular file with mode 0600`);
        }
        if (file.size > effectiveLimits().max_compressed_bytes) {
            fail(`${label} compressed-size limit exceeded`);
        }
        const hashes = new Map(Object.keys(expected).map(algorithm => [algorithm, createHash(algorithm)]));
        const chunks = [];
        let total = 0;
        while (total < file.size) {
            const chunk = Buffer.allocUnsafe(Math.min(1048576, file.size - total));
            const { bytesRead } = await handle.read(chunk, 0, chunk.length, null);
            if (bytesRead === 0) {
                fail(`${label} changed while being authenticated`);
            }
            const bytes = chunk.subarray(0, bytesRead);
            for (const hash of hashes.values()) {
                hash.update(bytes);
            }
            chunks.push(bytes);
            total += bytesRead;
        }
        for (const [algorithm, hash] of hashes) {
            if (hash.digest("hex") !== expected[algorithm]) {
                fail(`${label} ${algorithm.toUpperCase()} digest mismatch`);
            }
        }
        return Buffer.concat(chunks, total);
    } finally {
        await handle.close();
    }
}

async function readVerifiedCacheArchive(path, expected, label) {
    return readAuthenticatedArchive(path, expected, label, true);
}

function approvedHosts(lock, kind) {
    const override = kind === "npm" ? process.env.AGENTHARNESS_BOOTSTRAP_TEST_NPM_URL : process.env.AGENTHARNESS_BOOTSTRAP_TEST_RUNTIME_URL;
    const testHosts = process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE === "1" && override !== undefined && new URL(override).hostname === "127.0.0.1"
        ? ["127.0.0.1"]
        : [];
    if (kind === "npm") {
        return new Set([new URL(lock.package.tarball_url).hostname, new URL(lock.package.allowed_mirror_url).hostname, ...testHosts]);
    }
    return new Set(["github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com", ...lock.acquisition.mirror_policy.allowed_runtime_mirror_hosts, ...testHosts]);
}

async function downloadArtifact(url, destination, allowed, limit, expectedDigests, redirects = 0) {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || parsed.username !== "" || parsed.password !== "" || !allowed.has(parsed.hostname)) {
        fail("artifact URL or redirect is not approved HTTPS");
    }
    if (redirects > PRODUCTION_LIMITS.max_redirects) {
        fail("artifact redirect limit exceeded");
    }
    await new Promise((resolvePromise, rejectPromise) => {
        const operation = request(parsed, { headers: { "User-Agent": "agentharness-bootstrap/1", Accept: "application/octet-stream" }, timeout: 30000 }, response => {
            const status = response.statusCode ?? 0;
            if ([301, 302, 303, 307, 308].includes(status)) {
                response.resume();
                if (typeof response.headers.location !== "string") {
                    rejectPromise(new BootstrapError("artifact redirect is missing a location"));
                    return;
                }
                let next;
                try {
                    next = new URL(response.headers.location, parsed).href;
                } catch {
                    rejectPromise(new BootstrapError("artifact redirect is invalid"));
                    return;
                }
                downloadArtifact(next, destination, allowed, limit, expectedDigests, redirects + 1).then(resolvePromise, rejectPromise);
                return;
            }
            if (status !== 200) {
                response.resume();
                rejectPromise(new BootstrapError(`artifact download failed with HTTP ${status}`));
                return;
            }
            const declared = Number(response.headers["content-length"] ?? 0);
            if (!Number.isSafeInteger(declared) || declared < 0 || declared > limit) {
                response.resume();
                rejectPromise(new BootstrapError("artifact compressed-size limit exceeded"));
                return;
            }
            const output = createWriteStream(destination, { flags: "wx", mode: 0o600 });
            const responseHashes = new Map(
                Object.keys(expectedDigests).map(algorithm => [algorithm, createHash(algorithm)]),
            );
            let received = 0;
            let settled = false;
            const cleanup = error => {
                if (settled) {
                    return;
                }
                settled = true;
                response.destroy();
                output.destroy();
                rm(destination, { force: true }).then(() => rejectPromise(error), rejectPromise);
            };
            response.on("data", chunk => {
                received += chunk.length;
                for (const digest of responseHashes.values()) {
                    digest.update(chunk);
                }
                if (received > limit) {
                    cleanup(new BootstrapError("artifact compressed-size limit exceeded"));
                }
            });
            response.on("aborted", () => cleanup(new BootstrapError("artifact download ended before completion")));
            response.on("error", cleanup);
            output.on("error", cleanup);
            response.pipe(output);
            output.on("close", () => {
                if (settled) {
                    return;
                }
                if (declared !== 0 && received !== declared) {
                    cleanup(new BootstrapError("artifact download ended before completion"));
                    return;
                }
                for (const [algorithm, digest] of responseHashes) {
                    if (digest.digest("hex") !== expectedDigests[algorithm]) {
                        const message = algorithm === "sha512"
                            ? "artifact response SHA-512 digest mismatch"
                            : "artifact response SHA-256 digest mismatch";
                        cleanup(new BootstrapError(message));
                        return;
                    }
                }
                settled = true;
                resolvePromise();
            });
        });
        operation.on("timeout", () => operation.destroy(new BootstrapError("artifact download timed out")));
        operation.on("error", rejectPromise);
        operation.end();
    });
}

function decodeField(block, start, length, label) {
    const field = block.subarray(start, start + length);
    const zero = field.indexOf(0);
    const bytes = zero === -1 ? field : field.subarray(0, zero);
    try {
        return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch {
        fail(`${label} is not valid UTF-8`);
    }
}

function parseOctal(block, start, length, label) {
    const field = block.subarray(start, start + length);
    if ((field[0] & 0x80) !== 0) {
        fail(`${label} uses forbidden base-256 numeric data`);
    }
    const text = Buffer.from(field).toString("ascii").replace(/\0.*$/u, "").trim();
    if (text === "") {
        return 0;
    }
    if (!/^[0-7]+$/u.test(text)) {
        fail(`${label} contains invalid numeric data`);
    }
    const value = Number.parseInt(text, 8);
    if (!Number.isSafeInteger(value)) {
        fail(`${label} exceeds numeric bounds`);
    }
    return value;
}

function canonicalPath(name, limits, label = "archive path") {
    if (name.includes("\0") || name.includes("\\") || name.startsWith("/") || /^[A-Za-z]:/u.test(name)) {
        fail(`${label} is absolute or non-portable`);
    }
    const trimmed = name.endsWith("/") ? name.slice(0, -1) : name;
    if (Buffer.byteLength(trimmed, "utf8") > limits.max_path_bytes) {
        fail(`${label} length limit exceeded`);
    }
    const parts = trimmed.split("/");
    if (parts.length === 0 || parts.some(part => part === "" || part === "." || part === "..")) {
        fail(`${label} is noncanonical or traverses outside its root`);
    }
    return parts.join("/");
}

function parsePax(payload) {
    const result = Object.create(null);
    let offset = 0;
    while (offset < payload.length) {
        const space = payload.indexOf(0x20, offset);
        if (space === -1) {
            fail("PAX record length is invalid");
        }
        const lengthText = payload.subarray(offset, space).toString("ascii");
        if (!/^[1-9][0-9]*$/u.test(lengthText)) {
            fail("PAX record length is invalid");
        }
        const length = Number(lengthText);
        const end = offset + length;
        if (!Number.isSafeInteger(length) || end > payload.length || payload[end - 1] !== 0x0a) {
            fail("PAX record is truncated");
        }
        const record = payload.subarray(space + 1, end - 1);
        const equals = record.indexOf(0x3d);
        if (equals < 1) {
            fail("PAX record is invalid");
        }
        const key = record.subarray(0, equals).toString("ascii");
        if (!new Set(["path", "size"]).has(key) || Object.hasOwn(result, key)) {
            fail("PAX metadata key is unsupported or duplicate");
        }
        let value;
        try {
            value = new TextDecoder("utf-8", { fatal: true }).decode(record.subarray(equals + 1));
        } catch {
            fail("PAX metadata is not valid UTF-8");
        }
        result[key] = value;
        offset = end;
    }
    return result;
}

function effectiveLimits() {
    if (process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE === "1" && process.env.AGENTHARNESS_BOOTSTRAP_TEST_LIMITS !== undefined) {
        const overrides = parseJsonBytes(Buffer.from(process.env.AGENTHARNESS_BOOTSTRAP_TEST_LIMITS), "test limits");
        exactObject(overrides, "test limits", Object.keys(overrides));
        for (const [key, value] of Object.entries(overrides)) {
            if (!Object.hasOwn(PRODUCTION_LIMITS, key) || !Number.isSafeInteger(value) || value <= 0 || value > PRODUCTION_LIMITS[key]) {
                fail("test limits may only tighten known production bounds");
            }
        }
        return { ...PRODUCTION_LIMITS, ...overrides };
    }
    return PRODUCTION_LIMITS;
}

function parseTarGzip(payload, kind) {
    const limits = effectiveLimits();
    let tar;
    try {
        const tarOverhead = limits.max_members * 1024 + 1024;
        tar = gunzipSync(payload, { maxOutputLength: limits.max_expanded_bytes + tarOverhead });
    } catch {
        fail(`${kind} archive gzip data is invalid or exceeds its expanded-size limit`);
    }
    const members = [];
    const destinations = new Map();
    let pendingPax = null;
    let offset = 0;
    let endBlocks = 0;
    let expandedTotal = 0;
    while (offset + 512 <= tar.length) {
        const header = tar.subarray(offset, offset + 512);
        if (header.every(byte => byte === 0)) {
            endBlocks += 1;
            offset += 512;
            if (endBlocks === 2) {
                if (!tar.subarray(offset).every(byte => byte === 0)) {
                    fail(`${kind} TAR has ambiguous trailing data`);
                }
                break;
            }
            continue;
        }
        if (endBlocks !== 0) {
            fail(`${kind} TAR has an incomplete end marker`);
        }
        const storedChecksum = parseOctal(header, 148, 8, "TAR checksum");
        let checksum = 0;
        for (let index = 0; index < 512; index += 1) {
            checksum += index >= 148 && index < 156 ? 0x20 : header[index];
        }
        if (storedChecksum !== checksum) {
            fail(`${kind} TAR header checksum is invalid`);
        }
        const magic = header.subarray(257, 263).toString("binary");
        const version = header.subarray(263, 265).toString("binary");
        if (magic !== "ustar\0" || version !== "00") {
            fail(`${kind} TAR is not strict USTAR/PAX`);
        }
        let name = decodeField(header, 0, 100, "TAR name");
        const prefix = decodeField(header, 345, 155, "TAR prefix");
        if (prefix !== "") {
            name = `${prefix}/${name}`;
        }
        const mode = parseOctal(header, 100, 8, "TAR mode");
        let size = parseOctal(header, 124, 12, "TAR size");
        const typeByte = header[156];
        const type = typeByte === 0 ? "0" : String.fromCharCode(typeByte);
        const linkname = decodeField(header, 157, 100, "TAR link target");
        const dataStart = offset + 512;
        const padded = Math.ceil(size / 512) * 512;
        if (!Number.isSafeInteger(dataStart + padded) || dataStart + padded > tar.length) {
            fail(`${kind} TAR member data is truncated`);
        }
        let data = tar.subarray(dataStart, dataStart + size);
        offset = dataStart + padded;
        if (type === "x") {
            if (pendingPax !== null) {
                fail(`${kind} TAR has stacked PAX metadata`);
            }
            pendingPax = parsePax(data);
            continue;
        }
        if (["g", "L", "K", "S"].includes(type)) {
            fail(`${kind} TAR extension or sparse metadata is forbidden`);
        }
        if (pendingPax !== null) {
            if (pendingPax.path !== undefined) {
                name = pendingPax.path;
            }
            if (pendingPax.size !== undefined) {
                if (!/^(?:0|[1-9][0-9]*)$/u.test(pendingPax.size)) {
                    fail("PAX size is invalid");
                }
                const paxSize = Number(pendingPax.size);
                if (!Number.isSafeInteger(paxSize) || paxSize !== size) {
                    fail("PAX size does not match the authenticated member body");
                }
            }
            pendingPax = null;
        }
        if (!["0", "1", "2", "5"].includes(type)) {
            fail(`${kind} TAR member type is unsupported`);
        }
        const destination = canonicalPath(name, limits);
        if (destinations.has(destination)) {
            fail(`${kind} TAR has a duplicate destination`);
        }
        if (size > limits.max_member_bytes) {
            fail(`${kind} TAR member-size limit exceeded`);
        }
        if (type === "0") {
            expandedTotal += size;
            if (!Number.isSafeInteger(expandedTotal) || expandedTotal > limits.max_expanded_bytes) {
                fail(`${kind} archive expanded-size limit exceeded`);
            }
        }
        if (type !== "0" && size !== 0) {
            fail(`${kind} TAR non-file member contains data`);
        }
        if (members.length + 1 > limits.max_members) {
            fail(`${kind} TAR member-count limit exceeded`);
        }
        const member = { destination, type, mode: mode & 0o777, linkname, data: Buffer.from(data) };
        members.push(member);
        destinations.set(destination, member);
    }
    if (endBlocks !== 2 || pendingPax !== null) {
        fail(`${kind} TAR is truncated or has orphan metadata`);
    }
    for (const member of members) {
        const parts = member.destination.split("/");
        for (let index = 1; index < parts.length; index += 1) {
            const parent = destinations.get(parts.slice(0, index).join("/"));
            if (parent !== undefined && parent.type !== "5") {
                fail(`${kind} TAR has a file/directory collision`);
            }
        }
        if (member.type !== "5" && members.some(candidate => candidate.destination.startsWith(`${member.destination}/`))) {
            fail(`${kind} TAR has a file/directory collision`);
        }
    }
    validateLinkGraph(members, destinations);
    if (kind === "runtime") {
        if (!members.every(member => member.destination === "python" || member.destination.startsWith("python/")) || !destinations.has("python/bin/python3")) {
            fail("runtime archive has an unexpected top-level layout");
        }
        verifyRuntimeEntrypointMembers(destinations);
    } else if (!destinations.has("package/package.json") || !destinations.has("package/dist/agentharness.pyz") || members.some(member => !member.destination.startsWith("package/"))) {
        fail("npm archive has an unexpected top-level layout");
    }
    return members;
}

function linkTarget(member) {
    if (member.linkname.includes("\0") || member.linkname.includes("\\") || member.linkname.startsWith("/") || /^[A-Za-z]:/u.test(member.linkname)) {
        fail("archive link target is absolute or non-portable");
    }
    const base = member.type === "2" ? posix.dirname(member.destination) : ".";
    const target = posix.normalize(posix.join(base, member.linkname));
    if (target === ".." || target.startsWith("../") || target.startsWith("/")) {
        fail("archive link escapes extraction root");
    }
    return target;
}

function validateLinkGraph(members, destinations) {
    for (const member of members.filter(item => item.type === "1" || item.type === "2")) {
        let current = member;
        const seen = new Set([member.destination]);
        let depth = 0;
        while (current.type === "1" || current.type === "2") {
            depth += 1;
            if (depth > MAX_LINK_DEPTH) {
                fail("archive link graph depth limit exceeded");
            }
            const target = linkTarget(current);
            if (seen.has(target)) {
                fail("archive link graph is cyclic");
            }
            seen.add(target);
            current = destinations.get(target);
            if (current === undefined) {
                fail("archive link target is dangling");
            }
        }
        if (!["0", "5"].includes(current.type) || (member.type === "1" && current.type !== "0")) {
            fail("archive link terminal type is invalid");
        }
        member.terminal = current.destination;
        member.depth = depth;
    }
}

function verifyRuntimeEntrypointMembers(destinations) {
    const entrypoint = destinations.get("python/bin/python3");
    const terminal = entrypoint?.terminal === undefined
        ? entrypoint
        : destinations.get(entrypoint.terminal);
    if (terminal?.type !== "0" || (terminal.mode & 0o111) === 0) {
        fail("runtime entrypoint terminal must be a regular executable file");
    }
}

async function materializeArchive(root, members) {
    await mkdir(root, { recursive: false, mode: 0o700 });
    const ensureParents = async destination => mkdir(dirname(join(root, ...destination.split("/"))), { recursive: true, mode: 0o755 });
    for (const member of members.filter(item => item.type === "5")) {
        const destination = join(root, ...member.destination.split("/"));
        await mkdir(destination, { recursive: true, mode: member.mode || 0o755 });
        await chmod(destination, member.mode || 0o755);
    }
    for (const member of members.filter(item => item.type === "0")) {
        const destination = join(root, ...member.destination.split("/"));
        await ensureParents(member.destination);
        const handle = await open(destination, fsConstants.O_CREAT | fsConstants.O_EXCL | fsConstants.O_WRONLY | fsConstants.O_NOFOLLOW, member.mode || 0o644);
        try {
            await handle.writeFile(member.data);
            await handle.sync();
        } finally {
            await handle.close();
        }
        await chmod(destination, member.mode || 0o644);
    }
    for (const member of members.filter(item => item.type === "1").sort((left, right) => left.depth - right.depth)) {
        const destination = join(root, ...member.destination.split("/"));
        await ensureParents(member.destination);
        await hardlink(join(root, ...member.terminal.split("/")), destination);
    }
    for (const member of members.filter(item => item.type === "2").sort((left, right) => left.depth - right.depth)) {
        const destination = join(root, ...member.destination.split("/"));
        await ensureParents(member.destination);
        await symlink(member.linkname, destination);
    }
}

function crc32(payload) {
    let crc = 0xffffffff;
    for (const byte of payload) {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit += 1) {
            crc = (crc >>> 1) ^ ((crc & 1) === 1 ? 0xedb88320 : 0);
        }
    }
    return (crc ^ 0xffffffff) >>> 0;
}

function zipappIdentity(payload) {
    let eocd = -1;
    for (let offset = payload.length - 22; offset >= Math.max(0, payload.length - 65557); offset -= 1) {
        if (payload.readUInt32LE(offset) === 0x06054b50) {
            eocd = offset;
            break;
        }
    }
    if (eocd < 0 || payload.readUInt16LE(eocd + 4) !== 0 || payload.readUInt16LE(eocd + 6) !== 0 || payload.readUInt16LE(eocd + 8) !== payload.readUInt16LE(eocd + 10)) {
        fail("zipapp identity archive is invalid or uses unsupported ZIP features");
    }
    const count = payload.readUInt16LE(eocd + 10);
    const centralSize = payload.readUInt32LE(eocd + 12);
    let offset = payload.readUInt32LE(eocd + 16);
    if (offset + centralSize > eocd) {
        fail("zipapp central directory is truncated");
    }
    let selected = null;
    for (let index = 0; index < count; index += 1) {
        if (payload.readUInt32LE(offset) !== 0x02014b50) {
            fail("zipapp central directory is invalid");
        }
        const flags = payload.readUInt16LE(offset + 8);
        const method = payload.readUInt16LE(offset + 10);
        const checksum = payload.readUInt32LE(offset + 16);
        const compressedSize = payload.readUInt32LE(offset + 20);
        const expandedSize = payload.readUInt32LE(offset + 24);
        const nameLength = payload.readUInt16LE(offset + 28);
        const extraLength = payload.readUInt16LE(offset + 30);
        const commentLength = payload.readUInt16LE(offset + 32);
        const localOffset = payload.readUInt32LE(offset + 42);
        const name = payload.subarray(offset + 46, offset + 46 + nameLength).toString("utf8");
        if (name === "agentharness-runtime-identity.json") {
            if (selected !== null || flags & 1 || ![0, 8].includes(method) || expandedSize > MAX_JSON_BYTES || compressedSize > MAX_JSON_BYTES) {
                fail("zipapp identity member is duplicate, encrypted, oversized, or unsupported");
            }
            if (payload.readUInt32LE(localOffset) !== 0x04034b50) {
                fail("zipapp identity local header is invalid");
            }
            const localNameLength = payload.readUInt16LE(localOffset + 26);
            const localExtraLength = payload.readUInt16LE(localOffset + 28);
            const start = localOffset + 30 + localNameLength + localExtraLength;
            const compressed = payload.subarray(start, start + compressedSize);
            const expanded = method === 0 ? compressed : inflateRawSync(compressed, { maxOutputLength: MAX_JSON_BYTES });
            if (expanded.length !== expandedSize || crc32(expanded) !== checksum) {
                fail("zipapp identity member integrity is invalid");
            }
            selected = parseJsonBytes(expanded, "zipapp identity");
        }
        offset += 46 + nameLength + extraLength + commentLength;
    }
    if (selected === null) {
        fail("zipapp identity manifest is missing");
    }
    return validateIdentity(selected, "zipapp identity");
}

function identitiesEqual(lock, identity) {
    const normalizedPlugins = plugins => JSON.stringify(
        Object.entries(plugins).sort(([left], [right]) => left.localeCompare(right)),
    );
    return lock.zipapp.core_version === identity.core_version
        && lock.zipapp.schema_version === identity.schema_version
        && lock.zipapp.compatibility_provider_version === identity.compatibility_provider_version
        && normalizedPlugins(lock.zipapp.bundled_plugins) === normalizedPlugins(identity.bundled_plugins);
}

function inventoryFor(members) {
    const inventory = members.map(member => ({
        destination: member.destination,
        type: member.type,
        mode: member.mode,
        linkname: member.linkname,
        sha512: member.type === "0" ? createHash("sha512").update(member.data).digest("hex") : null,
    }));
    for (const item of inventory.filter(candidate => candidate.type === "1")) {
        const terminal = members.find(member => member.destination === item.destination)?.terminal;
        item.sha512 = inventory.find(candidate => candidate.destination === terminal)?.sha512 ?? null;
    }
    return inventory;
}

async function verifyInventory(root, inventory) {
    const expectedPaths = new Set([".artifact.tar.gz"]);
    const expectedDirectories = new Set();
    for (const member of inventory) {
        expectedPaths.add(member.destination);
        const parts = member.destination.split("/");
        for (let index = 1; index < parts.length; index += 1) {
            const parent = parts.slice(0, index).join("/");
            expectedPaths.add(parent);
            expectedDirectories.add(parent);
        }
        if (member.type === "5") {
            expectedDirectories.add(member.destination);
        }
    }
    const actualPaths = new Set();
    async function collect(directory, relative = "") {
        for (const entry of await readdir(directory, { withFileTypes: true })) {
            const destination = relative === "" ? entry.name : `${relative}/${entry.name}`;
            actualPaths.add(destination);
            if (entry.isDirectory()) {
                await collect(join(directory, entry.name), destination);
            }
        }
    }
    await collect(root);
    if (actualPaths.size !== expectedPaths.size
        || [...actualPaths].some(destination => !expectedPaths.has(destination))) {
        fail("verified cache inventory contains an unexpected or missing path");
    }
    const archive = await lstat(join(root, ".artifact.tar.gz"));
    const archiveOwnedByProcess = typeof process.getuid !== "function" || archive.uid === process.getuid();
    if (!archive.isFile() || !archiveOwnedByProcess || archive.nlink !== 1 || (archive.mode & 0o777) !== 0o600) {
        fail("verified cache archive must be a cache-owned regular file with mode 0600");
    }
    for (const destination of expectedDirectories) {
        if (!(await lstat(join(root, ...destination.split("/")))).isDirectory()) {
            fail("verified cache directory type changed");
        }
    }
    for (const member of inventory) {
        const destination = join(root, ...member.destination.split("/"));
        const info = await lstat(destination);
        const mode = info.mode & 0o777;
        if (member.type === "0" && (!info.isFile() || info.nlink < 1
            || mode !== (member.mode || 0o644)
            || await digestFile(destination, "sha512") !== member.sha512)) {
            fail("verified cache file changed");
        }
        if (member.type === "5" && (!info.isDirectory() || mode !== (member.mode || 0o755))) {
            fail("verified cache directory changed");
        }
        if (member.type === "2" && (!info.isSymbolicLink() || await readlink(destination) !== member.linkname)) {
            fail("verified cache symlink changed");
        }
        if (member.type === "1" && (!info.isFile() || await digestFile(destination, "sha512") !== member.sha512)) {
            fail("verified cache hardlink changed");
        }
    }
}

function verifyNpmIdentity(lock, members) {
    const packageMember = members.find(member => member.destination === "package/package.json");
    if (packageMember?.type !== "0") {
        fail("npm package identity manifest is missing");
    }
    const packageIdentity = parseJsonBytes(packageMember.data, "npm package identity");
    if (packageIdentity === null || typeof packageIdentity !== "object" || Array.isArray(packageIdentity)
        || packageIdentity.name !== lock.package.name || packageIdentity.version !== lock.package.version) {
        fail("npm package internal identity mismatch");
    }
    const zipappMember = members.find(member => member.destination === lock.zipapp.path);
    if (zipappMember?.type !== "0" || createHash("sha512").update(zipappMember.data).digest("hex") !== lock.zipapp.sha512) {
        fail("zipapp digest mismatch");
    }
    const identity = zipappIdentity(zipappMember.data);
    if (!identitiesEqual(lock, identity)) {
        fail("zipapp internal identity mismatch");
    }
}

async function loadCachedArtifact(cacheRoot, kind, digest, expected, lock = null) {
    const root = join(cacheRoot, kind, digest);
    const archivePath = join(root, ".artifact.tar.gz");
    try {
        await lstat(root);
    } catch (error) {
        if (error?.code === "ENOENT") {
            return null;
        }
        throw error;
    }
    const archive = await readVerifiedCacheArchive(archivePath, expected, `${kind} cache artifact`);
    const members = parseTarGzip(archive, kind);
    await verifyInventory(root, inventoryFor(members));
    if (lock !== null) {
        verifyNpmIdentity(lock, members);
    }
    return { root, members };
}

async function promoteArtifact(cacheRoot, kind, digest, archivePayload, members, sha256 = null) {
    const parent = join(cacheRoot, kind);
    const destination = join(parent, digest);
    const expectedDigests = sha256 === null
        ? { sha512: digest }
        : { sha512: digest, sha256 };
    await mkdir(parent, { recursive: true, mode: 0o700 });
    try {
        const cachedArchive = join(destination, ".artifact.tar.gz");
        const cached = await readVerifiedCacheArchive(cachedArchive, expectedDigests, `${kind} cache artifact`);
        const cachedMembers = parseTarGzip(cached, kind);
        await verifyInventory(destination, inventoryFor(cachedMembers));
        return destination;
    } catch (error) {
        if (error instanceof BootstrapError) {
            throw error;
        }
        if (error?.code !== "ENOENT") {
            fail("verified cache cannot be revalidated");
        }
    }
    const staging = await mkdtemp(join(parent, ".staging-"));
    try {
        const root = join(staging, "root");
        await materializeArchive(root, members);
        const stagedArchive = join(root, ".artifact.tar.gz");
        const archiveHandle = await open(
            stagedArchive,
            fsConstants.O_CREAT | fsConstants.O_EXCL | fsConstants.O_WRONLY | fsConstants.O_NOFOLLOW,
            0o600,
        );
        try {
            await archiveHandle.writeFile(archivePayload);
            await archiveHandle.sync();
        } finally {
            await archiveHandle.close();
        }
        await chmod(stagedArchive, 0o600);
        await readVerifiedCacheArchive(stagedArchive, expectedDigests, `${kind} staged artifact`);
        try {
            await rename(root, destination);
        } catch (error) {
            if (error?.code !== "EEXIST" && error?.code !== "ENOTEMPTY") {
                throw error;
            }
            const cachedArchive = join(destination, ".artifact.tar.gz");
            const cached = await readVerifiedCacheArchive(cachedArchive, expectedDigests, `${kind} cache artifact`);
            const cachedMembers = parseTarGzip(cached, kind);
            await verifyInventory(destination, inventoryFor(cachedMembers));
        }
        return destination;
    } finally {
        await rm(staging, { recursive: true, force: true });
    }
}

async function acquireArchive(options, lock, runtime, kind, temporaryRoot) {
    const authenticatedLocal = kind === "npm" ? options.authenticatedNpmArchive : options.authenticatedRuntimeArchive;
    const testLocal = kind === "npm" ? options.npmArchive : options.runtimeArchive;
    const local = authenticatedLocal ?? testLocal;
    const destination = join(temporaryRoot, `${kind}.tar.gz`);
    if (local !== null) {
        if (testLocal !== null && process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE !== "1") {
            fail("local artifacts are available only in explicit bootstrap test mode");
        }
    } else {
        const testOverride = kind === "npm" ? process.env.AGENTHARNESS_BOOTSTRAP_TEST_NPM_URL : process.env.AGENTHARNESS_BOOTSTRAP_TEST_RUNTIME_URL;
        const url = process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE === "1" && testOverride !== undefined
            ? testOverride
            : kind === "npm" ? lock.package.tarball_url : runtime.url;
        const expectedDigests = kind === "npm"
            ? { sha512: lock.package.sha512 }
            : { sha512: runtime.sha512, sha256: runtime.sha256 };
        await downloadArtifact(
            url,
            destination,
            approvedHosts(lock, kind),
            PRODUCTION_LIMITS.max_compressed_bytes,
            expectedDigests,
        );
    }
    const expectedDigests = kind === "npm"
        ? { sha512: lock.package.sha512 }
        : { sha512: runtime.sha512, sha256: runtime.sha256 };
    const sourcePath = local ?? destination;
    return {
        payload: await readAuthenticatedArchive(sourcePath, expectedDigests, `${kind} artifact`),
        sourcePath,
    };
}

async function exerciseTestSwapAfterSnapshot(sourcePath) {
    if (process.env.AGENTHARNESS_BOOTSTRAP_TEST_MODE !== "1"
        || process.env.AGENTHARNESS_BOOTSTRAP_TEST_SWAP_RUNTIME_AFTER_AUTH === undefined) {
        return;
    }
    const original = await readFile(sourcePath);
    const replacement = await readFile(process.env.AGENTHARNESS_BOOTSTRAP_TEST_SWAP_RUNTIME_AFTER_AUTH);
    await writeFile(sourcePath, replacement);
    await writeFile(sourcePath, original);
}

async function launchVerified(options, lock, runtime, npmCache, runtimeCache) {
    const zipappPath = join(npmCache.root, ...lock.zipapp.path.split("/"));
    const interpreterPath = join(runtimeCache.root, ...runtime.interpreter_path.split("/"));
    await verifyInventory(npmCache.root, inventoryFor(npmCache.members));
    await verifyInventory(runtimeCache.root, inventoryFor(runtimeCache.members));
    if (await digestFile(zipappPath, "sha512") !== lock.zipapp.sha512) {
        fail("verified zipapp changed before launch");
    }
    const interpreterReal = await realpath(interpreterPath);
    const runtimeRootReal = await realpath(runtimeCache.root);
    const interpreterRelative = relative(runtimeRootReal, interpreterReal);
    if (interpreterRelative === "" || interpreterRelative === ".."
        || interpreterRelative.startsWith(`..${sep}`) || isAbsolute(interpreterRelative)) {
        fail("verified interpreter resolves outside runtime cache");
    }
    const interpreter = await stat(interpreterPath);
    if (!interpreter.isFile() || (interpreter.mode & 0o111) === 0) {
        fail("verified runtime entrypoint terminal is not a regular executable file");
    }
    if (options.verifyOnly) {
        return 0;
    }
    const forwardedArguments = options.forwarded;
    return await new Promise((resolvePromise, rejectPromise) => {
        const child = spawn(interpreterPath, [zipappPath, ...forwardedArguments], { stdio: "inherit", shell: false });
        child.on("error", rejectPromise);
        child.on("exit", (code, signal) => signal === null ? resolvePromise(code ?? 1) : rejectPromise(new BootstrapError("verified runtime terminated by signal")));
    });
}

function parseArguments(arguments_) {
    const result = { lock: null, cache: null, npmArchive: null, runtimeArchive: null, authenticatedNpmArchive: null, authenticatedRuntimeArchive: null, verifyOnly: false, forwarded: [] };
    for (let index = 0; index < arguments_.length; index += 1) {
        const argument = arguments_[index];
        if (argument === "--") {
            result.forwarded = arguments_.slice(index + 1);
            break;
        }
        if (argument === "--verify-only") {
            result.verifyOnly = true;
            continue;
        }
        const key = { "--lock": "lock", "--cache": "cache", "--npm-archive": "npmArchive", "--runtime-archive": "runtimeArchive", "--authenticated-npm-archive": "authenticatedNpmArchive", "--authenticated-runtime-archive": "authenticatedRuntimeArchive" }[argument];
        if (key === undefined || index + 1 >= arguments_.length) {
            fail("usage: verify-runtime.mjs --lock PATH --cache PATH [-- ARGS...]");
        }
        result[key] = arguments_[index + 1];
        index += 1;
    }
    const testPairInvalid = (result.npmArchive === null) !== (result.runtimeArchive === null);
    const authenticatedPairInvalid = (result.authenticatedNpmArchive === null) !== (result.authenticatedRuntimeArchive === null);
    const mixedLocalModes = result.npmArchive !== null && result.authenticatedNpmArchive !== null;
    if (result.lock === null || result.cache === null || testPairInvalid || authenticatedPairInvalid || mixedLocalModes) {
        fail("both lock/cache and paired test archives are required");
    }
    return result;
}

async function run() {
    const options = parseArguments(process.argv.slice(2));
    const lockPayload = await readFile(options.lock);
    const lock = validateLock(parseJsonBytes(lockPayload, "consumer runtime lock"));
    const runtime = selectedRuntime(lock);
    const requestedCacheRoot = resolve(options.cache);
    await mkdir(requestedCacheRoot, { recursive: true, mode: 0o700 });
    const cacheRoot = await realpath(requestedCacheRoot);
    const cachedNpm = await loadCachedArtifact(cacheRoot, "npm", lock.package.sha512, { sha512: lock.package.sha512 }, lock);
    const cachedRuntime = await loadCachedArtifact(cacheRoot, "runtime", runtime.sha512, { sha512: runtime.sha512, sha256: runtime.sha256 });
    if (cachedNpm !== null && cachedRuntime !== null) {
        return launchVerified(options, lock, runtime, cachedNpm, cachedRuntime);
    }
    const temporaryParent = dirname(cacheRoot);
    await mkdir(temporaryParent, { recursive: true, mode: 0o700 });
    const temporaryRoot = await mkdtemp(join(temporaryParent, ".agentharness-download-"));
    try {
        const npmArchive = await acquireArchive(options, lock, runtime, "npm", temporaryRoot);
        const runtimeArchive = await acquireArchive(options, lock, runtime, "runtime", temporaryRoot);
        await exerciseTestSwapAfterSnapshot(runtimeArchive.sourcePath);
        const npmMembers = parseTarGzip(npmArchive.payload, "npm");
        const runtimeMembers = parseTarGzip(runtimeArchive.payload, "runtime");
        verifyNpmIdentity(lock, npmMembers);
        const npmRoot = await promoteArtifact(cacheRoot, "npm", lock.package.sha512, npmArchive.payload, npmMembers);
        const runtimeRoot = await promoteArtifact(
            cacheRoot,
            "runtime",
            runtime.sha512,
            runtimeArchive.payload,
            runtimeMembers,
            runtime.sha256,
        );
        return launchVerified(
            options,
            lock,
            runtime,
            { root: npmRoot, members: npmMembers },
            { root: runtimeRoot, members: runtimeMembers },
        );
    } finally {
        await rm(temporaryRoot, { recursive: true, force: true });
    }
}

try {
    process.exitCode = await run();
} catch (error) {
    const message = error instanceof BootstrapError ? error.message : "bootstrap verification failed safely";
    const safeMessage = message.replace(/[\u0000-\u001f\u007f-\u009f]/gu, character => {
        const code = character.codePointAt(0).toString(16).padStart(4, "0");
        return `\\u${code}`;
    });
    process.stderr.write(`agentharness bootstrap: ${safeMessage}. Remove the affected cache entry and retry with the committed runtime lock.\n`);
    process.exitCode = 1;
}
