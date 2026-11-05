"""Summarise a .glb: node tree (names, transforms) and world-space bounds from accessor min/max.
  python3 glbinfo.py file.glb [maxnodes]"""
import json, struct, sys


def load(path):
    b = open(path, "rb").read()
    assert b[:4] == b"glTF"
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n])


def mat_mul(a, b):
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def node_matrix(nd):
    if "matrix" in nd:  # column-major
        m = nd["matrix"]
        return [m[c * 4 + r] for r in range(4) for c in range(4)]
    t = nd.get("translation", [0, 0, 0]); s = nd.get("scale", [1, 1, 1]); x, y, z, w = nd.get("rotation", [0, 0, 0, 1])
    R = [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
         2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
         2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]
    return [R[0] * s[0], R[1] * s[1], R[2] * s[2], t[0], R[3] * s[0], R[4] * s[1], R[5] * s[2], t[1],
            R[6] * s[0], R[7] * s[1], R[8] * s[2], t[2], 0, 0, 0, 1]


def main():
    g = load(sys.argv[1]); maxn = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    lo, hi = [1e9] * 3, [-1e9] * 3
    printed = [0]

    def walk(i, M, depth):
        nd = g["nodes"][i]
        W = mat_mul(M, node_matrix(nd))
        if printed[0] < maxn:
            print("  " * depth + f"{nd.get('name', '?')}" + (" [mesh]" if "mesh" in nd else ""))
            printed[0] += 1
        if "mesh" in nd:
            for prim in g["meshes"][nd["mesh"]]["primitives"]:
                a = g["accessors"][prim["attributes"]["POSITION"]]
                for cx in (a["min"][0], a["max"][0]):
                    for cy in (a["min"][1], a["max"][1]):
                        for cz in (a["min"][2], a["max"][2]):
                            p = [W[r * 4] * cx + W[r * 4 + 1] * cy + W[r * 4 + 2] * cz + W[r * 4 + 3] for r in range(3)]
                            for k in range(3):
                                lo[k] = min(lo[k], p[k]); hi[k] = max(hi[k], p[k])
        for c in nd.get("children", []):
            walk(c, W, depth + 1)

    I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r, I, 0)
    print("nodes", len(g["nodes"]), "meshes", len(g["meshes"]), "materials", len(g.get("materials", [])))
    print("bounds min", [round(v, 5) for v in lo], "max", [round(v, 5) for v in hi])


main()
