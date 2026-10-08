"""BK-tree over 64-bit hashes, Hamming metric. Node = [hash, ids, {distance: child}]."""


class BKTree:
    def __init__(self):
        self.root = None

    def add(self, h: int, id: int):
        if self.root is None:
            self.root = [h, [id], {}]
            return
        n = self.root
        while True:
            d = (n[0] ^ h).bit_count()
            if d == 0:
                n[1].append(id)
                return
            if d not in n[2]:
                n[2][d] = [h, [id], {}]
                return
            n = n[2][d]

    def search(self, h: int, tol: int) -> list[tuple[int, int]]:
        """All (id, distance) with distance <= tol. Triangle inequality prunes children."""
        out, stack = [], [self.root] if self.root else []
        while stack:
            n = stack.pop()
            d = (n[0] ^ h).bit_count()
            if d <= tol:
                out += [(i, d) for i in n[1]]
            stack += [c for k, c in n[2].items() if d - tol <= k <= d + tol]
        return out


if __name__ == "__main__":  # self-check: tree must agree with brute force
    import random

    hs = [random.getrandbits(64) for _ in range(2000)]
    t = BKTree()
    for i, h in enumerate(hs):
        t.add(h, i)
    for _ in range(50):
        q = hs[random.randrange(len(hs))] ^ random.getrandbits(5)  # near-duplicate
        want = sorted((i, (h ^ q).bit_count()) for i, h in enumerate(hs) if (h ^ q).bit_count() <= 10)
        assert sorted(t.search(q, 10)) == want and want
    print("bktree ok")
