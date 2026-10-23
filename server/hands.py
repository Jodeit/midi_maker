"""Assign notes to left/right hand with a small beam search.

Notes that start together form a chord. For each chord we try every split of its
pitch-sorted notes (lowest k -> left hand) and score it on hand span, register,
and continuity with where each hand just was. A beam keeps the best few paths.
Heuristic, not a trained model: crossings and interleaved voices can still be wrong.
"""
GROUP_WINDOW = 0.06   # seconds: onsets this close are one chord
LH_HOME, RH_HOME = 48, 70
BEAM = 16
FORGET = 2.5          # seconds of silence before a hand's position is forgotten


def _span_cost(ps):
    if len(ps) < 2:
        return 0.0
    s = max(ps) - min(ps)
    c = max(0, s - 9) * 1.0 + max(0, s - 14) * 5.0
    return c + max(0, len(ps) - 5) * 10.0


def _hand_cost(ps, home, prev, prev_other, other_is_higher):
    if not ps:
        return 0.0
    mean = sum(ps) / len(ps)
    c = _span_cost(ps) + 0.08 * abs(mean - home)
    if prev is not None:
        c += 0.15 * min(abs(mean - prev), 24)
    # crossing: a hand landing past where the other hand just was
    if prev_other is not None:
        if other_is_higher and mean > prev_other + 2:
            c += 3.0
        if not other_is_higher and mean < prev_other - 2:
            c += 3.0
    return c


def split_hands(notes):
    """notes: pretty_midi.Note list -> (right_hand_notes, left_hand_notes)."""
    notes = sorted(notes, key=lambda n: (n.start, n.pitch))
    groups, cur = [], []
    for n in notes:
        if cur and n.start - cur[0].start > GROUP_WINDOW:
            groups.append(cur); cur = []
        cur.append(n)
    if cur:
        groups.append(cur)
    for g in groups:  # onsets within a chord differ slightly, so sort by pitch explicitly
        g.sort(key=lambda n: n.pitch)

    # state: (cost, lh_pos, rh_pos, last_time, assignment)  assignment: list of k per group
    beam = [(0.0, None, None, -1e9, [])]
    for g in groups:
        ps = [n.pitch for n in g]  # already sorted ascending
        t = g[0].start
        nxt = []
        for cost, lp, rp, lt, assign in beam:
            if t - lt > FORGET:
                lp = rp = None
            for k in range(len(ps) + 1):
                left, right = ps[:k], ps[k:]
                c = cost + _hand_cost(left, LH_HOME, lp, rp, other_is_higher=True) \
                         + _hand_cost(right, RH_HOME, rp, lp, other_is_higher=False)
                nlp = (sum(left) / len(left)) if left else lp
                nrp = (sum(right) / len(right)) if right else rp
                nxt.append((c, nlp, nrp, t, assign + [k]))
        nxt.sort(key=lambda s: s[0])
        beam = nxt[:BEAM]

    best = beam[0][4]
    rh, lh = [], []
    for g, k in zip(groups, best):
        lh.extend(g[:k]); rh.extend(g[k:])
    return rh, lh
