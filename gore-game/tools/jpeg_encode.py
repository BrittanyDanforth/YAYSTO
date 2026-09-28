"""Tiny baseline JPEG encoder in pure numpy (no Pillow needed).

Why: Blender's own JPEG writer always uses 4:2:0 chroma subsampling and the
standard Huffman tables.  Tangent-space normal maps and packed ORM maps store
independent data in R/G/B, so halving the chroma resolution smears them.  This
encoder writes baseline (SOF0) JFIF files that every browser decodes, with

* 4:4:4 (no subsampling) or 4:2:0, per image,
* IJG quality scaling of the Annex K quantisation tables,
* optimised Huffman tables (two passes, like ``cjpeg -optimize``),
* optional grayscale output.

Usage::

    from jpeg_encode import encode_jpeg
    data = encode_jpeg(rgb_uint8_hxwx3, quality=92, subsample=False)

Rows are top to bottom (row 0 is the top of the image), like every image file.
"""
import struct

import numpy as np

_ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63])

_Q_LUMA = np.array([
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99])
_Q_CHROMA = np.array([
    17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99])


def _qtable(base, quality):
    quality = int(min(max(quality, 1), 100))
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    return np.clip((base * scale + 50) // 100, 1, 255).astype(np.int32)


def _dct_matrix():
    m = np.zeros((8, 8))
    for u in range(8):
        a = np.sqrt(1.0 / 8.0) if u == 0 else 0.5
        for x in range(8):
            m[u, x] = a * np.cos((2 * x + 1) * u * np.pi / 16.0)
    return m


_DCT = _dct_matrix()


def _blocks(plane):
    """(H, W) plane with H, W multiples of 8 -> (H/8 * W/8, 8, 8) raster order."""
    h, w = plane.shape
    return plane.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8)


def _quantise(blocks, q):
    """Forward DCT + quantisation -> (N, 64) int32 coefficients in zig-zag order."""
    coef = np.einsum('ux,nxy,vy->nuv', _DCT, blocks - 128.0, _DCT, optimize=True).reshape(-1, 64)
    out = np.rint(coef / q[None, :]).astype(np.int32)
    return out[:, _ZIGZAG]


def _bitlen(v):
    """JPEG magnitude category (number of bits of |v|), vectorised."""
    a = np.abs(v).astype(np.int64)
    n = np.zeros(a.shape, np.int64)
    while True:
        m = a > 0
        if not m.any():
            return n
        n += m
        a >>= 1


def _symbols(zz, comp):
    """Entropy-coding symbols for blocks `zz` (N, 64) in scan order.

    comp: (N,) component index per block (for DC prediction and table choice).
    Returns sorted arrays (table_class_is_ac, table_id, symbol, extra_value, extra_len).
    """
    n = zz.shape[0]
    # ---- DC: difference to the previous block of the same component --------
    dc = zz[:, 0].astype(np.int64)
    diff = np.empty(n, np.int64)
    for c in np.unique(comp):
        idx = np.nonzero(comp == c)[0]
        d = dc[idx]
        diff[idx] = d - np.concatenate([[0], d[:-1]])
    dsz = _bitlen(diff)
    dval = np.where(diff < 0, diff + (1 << dsz) - 1, diff)
    keys = [np.arange(n, dtype=np.int64) * 1000]
    is_ac = [np.zeros(n, bool)]
    tid = [comp.astype(np.int64)]
    sym = [dsz]
    ev = [dval]
    el = [dsz]
    # ---- AC -----------------------------------------------------------------
    ac = zz[:, 1:]
    bi, ki = np.nonzero(ac)
    ki = ki + 1                                      # zig-zag position 1..63
    vals = ac[bi, ki - 1].astype(np.int64)
    first = np.ones(len(bi), bool)
    first[1:] = bi[1:] != bi[:-1]
    prev = np.empty(len(bi), np.int64)
    prev[0] = 0
    prev[1:] = ki[:-1]
    prev[first] = 0
    run = ki - prev - 1
    nzrl = run // 16
    run = run % 16
    asz = _bitlen(vals)
    aval = np.where(vals < 0, vals + (1 << asz) - 1, vals)
    keys.append(bi.astype(np.int64) * 1000 + ki * 10 + 5)
    is_ac.append(np.ones(len(bi), bool))
    tid.append(comp[bi].astype(np.int64))
    sym.append((run << 4) | asz)
    ev.append(aval)
    el.append(asz)
    for j in range(3):                               # zero runs of 16 (ZRL = 0xF0)
        m = nzrl > j
        if m.any():
            keys.append(bi[m].astype(np.int64) * 1000 + ki[m] * 10 + j)
            is_ac.append(np.ones(m.sum(), bool))
            tid.append(comp[bi[m]].astype(np.int64))
            sym.append(np.full(m.sum(), 0xF0, np.int64))
            ev.append(np.zeros(m.sum(), np.int64))
            el.append(np.zeros(m.sum(), np.int64))
    # ---- EOB for blocks that do not end on a non-zero coefficient 63 --------
    last = np.zeros(n, np.int64)
    np.maximum.at(last, bi, ki)
    eob = np.nonzero(last < 63)[0]
    keys.append(eob.astype(np.int64) * 1000 + 999)
    is_ac.append(np.ones(len(eob), bool))
    tid.append(comp[eob].astype(np.int64))
    sym.append(np.zeros(len(eob), np.int64))
    ev.append(np.zeros(len(eob), np.int64))
    el.append(np.zeros(len(eob), np.int64))
    keys = np.concatenate(keys)
    order = np.argsort(keys, kind='stable')
    return (np.concatenate(is_ac)[order], np.concatenate(tid)[order], np.concatenate(sym)[order],
            np.concatenate(ev)[order], np.concatenate(el)[order])


def _optimal_table(freq):
    """libjpeg's jpeg_gen_optimal_table: (bits[1..16], huffval list) from symbol counts."""
    freq = list(freq) + [1]                          # reserved symbol 256 so no code is all ones
    freq = freq[:257] if len(freq) > 257 else freq + [0] * (257 - len(freq))
    freq[256] = 1
    codesize = [0] * 257
    others = [-1] * 257
    while True:
        c1, v = -1, 1 << 62
        for i in range(257):
            if 0 < freq[i] <= v:
                v, c1 = freq[i], i
        c2, v = -1, 1 << 62
        for i in range(257):
            if 0 < freq[i] <= v and i != c1:
                v, c2 = freq[i], i
        if c2 < 0:
            break
        freq[c1] += freq[c2]
        freq[c2] = 0
        codesize[c1] += 1
        while others[c1] >= 0:
            c1 = others[c1]
            codesize[c1] += 1
        others[c1] = c2
        codesize[c2] += 1
        while others[c2] >= 0:
            c2 = others[c2]
            codesize[c2] += 1
    bits = [0] * 33
    for i in range(257):
        if codesize[i]:
            bits[codesize[i]] += 1
    for i in range(32, 16, -1):
        while bits[i] > 0:
            j = i - 2
            while bits[j] == 0:
                j -= 1
            bits[i] -= 2
            bits[i - 1] += 1
            bits[j + 1] += 2
            bits[j] -= 1
    i = 16
    while bits[i] == 0:
        i -= 1
    bits[i] -= 1                                     # drop the reserved symbol
    huffval = []
    for size in range(1, 33):
        for s in range(256):
            if codesize[s] == size:
                huffval.append(s)
    return bits[1:17], huffval


def _codes(bits, huffval):
    """Canonical code (value, length) lookup arrays indexed by symbol."""
    code_of = np.zeros(256, np.int64)
    len_of = np.zeros(256, np.int64)
    code, k = 0, 0
    for length in range(1, 17):
        for _ in range(bits[length - 1]):
            s = huffval[k]
            code_of[s] = code
            len_of[s] = length
            code += 1
            k += 1
        code <<= 1
    return code_of, len_of


def _pack_bits(values, lengths):
    """Concatenate variable-length big-endian codes; pad with 1s; byte-stuff 0xFF."""
    total = int(lengths.sum())
    offs = np.concatenate([[0], np.cumsum(lengths)[:-1]])
    nbytes = (total + 7) // 8
    bits = np.ones(nbytes * 8, np.uint8)             # padding bits are 1
    maxlen = int(lengths.max()) if len(lengths) else 0
    for j in range(maxlen):
        m = lengths > j
        pos = offs[m] + j
        bits[pos] = ((values[m] >> (lengths[m] - 1 - j)) & 1).astype(np.uint8)
    data = np.packbits(bits)
    ff = np.nonzero(data == 0xFF)[0]
    if len(ff):
        data = np.insert(data, ff + 1, 0)
    return data.tobytes()


def _segment(marker, payload):
    return struct.pack('>HH', marker, len(payload) + 2) + payload


def encode_jpeg(img, quality=90, subsample=False, quality_chroma=None):
    """Encode an (H, W, 3) or (H, W) uint8 array (row 0 = top) as baseline JPEG bytes."""
    img = np.asarray(img)
    gray = img.ndim == 2
    h, w = img.shape[:2]
    f = img.astype(np.float64)
    if gray:
        planes = [f]
    else:
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        planes = [0.299 * r + 0.587 * g + 0.114 * b,
                  -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0,
                  0.5 * r - 0.418688 * g - 0.081312 * b + 128.0]
    sub = subsample and not gray
    mcu = 16 if sub else 8
    ph, pw = -(-h // mcu) * mcu, -(-w // mcu) * mcu

    def pad(p):
        return np.pad(p, ((0, ph - p.shape[0]), (0, pw - p.shape[1])), mode='edge')

    planes = [pad(p) for p in planes]
    qy = _qtable(_Q_LUMA, quality)
    qc = _qtable(_Q_CHROMA, quality_chroma if quality_chroma is not None else quality)
    if gray:
        zz = _quantise(_blocks(planes[0]), qy)
        comp = np.zeros(len(zz), np.int64)
    elif not sub:
        zy = _quantise(_blocks(planes[0]), qy)
        zb = _quantise(_blocks(planes[1]), qc)
        zr = _quantise(_blocks(planes[2]), qc)
        zz = np.stack([zy, zb, zr], 1).reshape(-1, 64)
        comp = np.tile(np.array([0, 1, 2]), len(zy))
    else:
        cb = planes[1].reshape(ph // 2, 2, pw // 2, 2).mean((1, 3))
        cr = planes[2].reshape(ph // 2, 2, pw // 2, 2).mean((1, 3))
        zy = _quantise(_blocks(planes[0]), qy)             # raster order of 8x8 blocks
        by, bx = ph // 8, pw // 8
        zy = zy.reshape(by // 2, 2, bx // 2, 2, 64).transpose(0, 2, 1, 3, 4).reshape(-1, 4, 64)
        zb = _quantise(_blocks(cb), qc)[:, None]
        zr = _quantise(_blocks(cr), qc)[:, None]
        zz = np.concatenate([zy, zb, zr], 1).reshape(-1, 64)
        comp = np.tile(np.array([0, 0, 0, 0, 1, 2]), len(zb))
    is_ac, tid, sym, ev, el = _symbols(zz, comp)
    table_sel = np.minimum(tid, 1)                     # 0 = luma tables, 1 = chroma tables
    ntab = 1 if gray else 2
    tables = {}
    dht = b''
    for ac in (0, 1):
        for t in range(ntab):
            m = (is_ac == bool(ac)) & (table_sel == t)
            freq = np.bincount(sym[m], minlength=256)[:256]
            bits, huffval = _optimal_table(freq.tolist())
            tables[(ac, t)] = _codes(bits, huffval)
            dht += bytes([(ac << 4) | t]) + bytes(bits) + bytes(huffval)
    values = np.empty(len(sym), np.int64)
    lengths = np.empty(len(sym), np.int64)
    for (ac, t), (code_of, len_of) in tables.items():
        m = (is_ac == bool(ac)) & (table_sel == t)
        s = sym[m]
        values[m] = (code_of[s] << el[m]) | ev[m]
        lengths[m] = len_of[s] + el[m]
    scan = _pack_bits(values, lengths)

    out = b'\xff\xd8'
    out += _segment(0xFFE0, b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
    dqt = bytes([0]) + bytes(qy[_ZIGZAG].astype(np.uint8))
    if not gray:
        dqt += bytes([1]) + bytes(qc[_ZIGZAG].astype(np.uint8))
    out += _segment(0xFFDB, dqt)
    if gray:
        sof = struct.pack('>BHHB', 8, h, w, 1) + bytes([1, 0x11, 0])
    else:
        ysamp = 0x22 if sub else 0x11
        sof = struct.pack('>BHHB', 8, h, w, 3) + bytes([1, ysamp, 0, 2, 0x11, 1, 3, 0x11, 1])
    out += _segment(0xFFC0, sof)
    out += _segment(0xFFC4, dht)
    if gray:
        sos = bytes([1, 1, 0x00]) + bytes([0, 63, 0])
    else:
        sos = bytes([3, 1, 0x00, 2, 0x11, 3, 0x11]) + bytes([0, 63, 0])
    out += _segment(0xFFDA, sos)
    out += scan + b'\xff\xd9'
    return out


if __name__ == '__main__':
    # quick self test: gradient + noise, decode with Blender if available
    rng = np.random.default_rng(1)
    yy, xx = np.mgrid[0:250, 0:333]
    test = np.stack([xx * 255 / 333, yy * 255 / 250, (xx + yy) % 256], -1)
    test = np.clip(test + rng.normal(0, 8, test.shape), 0, 255).astype(np.uint8)
    for s in (False, True):
        d = encode_jpeg(test, 90, subsample=s)
        print('subsample', s, len(d), 'bytes')
