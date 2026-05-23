from itertools import combinations
from collections import defaultdict
import tkinter as tk
from tkinter import scrolledtext, font

def canonical(a, b):
    return (a, b) if a < b else (b, a)


def minimize_fsm(states, inputs, transitions, outputs, mtype):
    ordered = sorted(states)
    all_pairs = [canonical(a, b) for a, b in combinations(ordered, 2)]

    table = {}
    for p in all_pairs:
        si, sj = p
        diff = False
        for inp in inputs:
            oi = outputs.get((si, inp) if mtype == 'mealy' else si)
            oj = outputs.get((sj, inp) if mtype == 'mealy' else sj)
            if oi != oj:
                diff = True
                break
        table[p] = False if diff else set()

    cell_display = {}
    for p in all_pairs:
        si, sj = p
        label_parts = []
        for inp in inputs:
            ni = transitions.get((si, inp))
            nj = transitions.get((sj, inp))
            if ni and nj and ni != nj:
                label_parts.append(f"{ni}-{nj}")
        cell_display[p] = "\n".join(label_parts) if label_parts else ""

        if table[p] is not False:
            for inp in inputs:
                ni = transitions.get((si, inp))
                nj = transitions.get((sj, inp))
                if ni and nj and ni != nj:
                    dep = canonical(ni, nj)
                    if dep != p:
                        table[p].add(dep)

    changed = True
    while changed:
        changed = False
        for p in all_pairs:
            if table[p] is False:
                continue
            for dep in list(table[p]):
                if table[dep] is False:
                    table[p] = False
                    changed = True
                    break

    parent = {s: s for s in states}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for p in all_pairs:
        if table[p] is not False:
            union(p[0], p[1])

    groups = defaultdict(list)
    for s in sorted(states):
        groups[find(s)].append(s)

    classes = sorted(groups.values(), key=lambda g: g[0])
    rep = {s: g[0] for g in classes for s in g}

    min_states = sorted({rep[s] for s in states})
    min_trans = {}
    min_out = {}

    for s in min_states:
        if mtype == 'moore':
            min_out[s] = outputs[s]
        for inp in inputs:
            ns = transitions.get((s, inp))
            if ns:
                min_trans[(s, inp)] = rep[ns]
            if mtype == 'mealy':
                out = outputs.get((s, inp))
                if out is not None:
                    min_out[(s, inp)] = out

    return table, cell_display, classes, rep, min_states, min_trans, min_out, ordered


def build_log(states, inputs, transitions, outputs, mtype,
              table, cell_display, classes, rep, min_states, min_trans, min_out, ordered):
    lines = []

    lines.append("=" * 56)
    lines.append("  STEP 1 — Initial table (distinguish by output)")
    lines.append("=" * 56)
    all_pairs = [canonical(a, b) for a, b in combinations(ordered, 2)]
    for p in all_pairs:
        si, sj = p
        status = "✗  [output mismatch]" if table[p] is False and not cell_display[p] else (
            "✓  [outputs match]" if table[p] is not False else "✗  [output mismatch]"
        )
        lines.append(f"  ({si},{sj})  →  {status}")

    lines.append("")
    lines.append("=" * 56)
    lines.append("  STEP 2 — Fill implications")
    lines.append("=" * 56)
    for p in all_pairs:
        si, sj = p
        disp = cell_display[p]
        if not disp:
            lines.append(f"  ({si},{sj})  →  no dependencies (equivalent)")
        else:
            lines.append(f"  ({si},{sj})  →  depends on: {disp.replace(chr(10), ', ')}")

    lines.append("")
    lines.append("=" * 56)
    lines.append("  STEP 3 — Propagate crossings")
    lines.append("=" * 56)
    crossed = [p for p in all_pairs if table[p] is False and cell_display[p]]
    if crossed:
        for p in crossed:
            lines.append(f"  ({p[0]},{p[1]})  →  crossed (implied pair was eliminated)")
    else:
        lines.append("  nothing to propagate")

    lines.append("")
    lines.append("=" * 56)
    lines.append("  STEP 4 — Equivalence classes")
    lines.append("=" * 56)
    for cls in classes:
        r = cls[0]
        lines.append(f"  {{{', '.join(cls)}}}  →  representative: {r}")

    lines.append("")
    lines.append("=" * 56)
    lines.append("  STEP 5 — Minimized machine")
    lines.append("=" * 56)
    lines.append(f"  States : {min_states}")
    lines.append(f"  Inputs : {inputs}")
    lines.append("")
    for s in min_states:
        for inp in inputs:
            ns = min_trans.get((s, inp), '-')
            if mtype == 'mealy':
                out = min_out.get((s, inp), '-')
                lines.append(f"    δ({s},{inp}) = {ns}    λ({s},{inp}) = {out}")
            else:
                lines.append(f"    δ({s},{inp}) = {ns}    λ({s}) = {min_out.get(s, '-')}")

    lines.append("")
    lines.append(f"  {len(states)} states  →  {len(min_states)} states")
    if len(min_states) < len(states):
        lines.append(f"  saved {len(states) - len(min_states)} state(s)")
    else:
        lines.append("  machine is already minimal")

    return "\n".join(lines)

def parse_table(raw_text, inputs, mtype):
    lines = [l for l in raw_text.strip().splitlines() if l.strip()]
    states, transitions, outputs = [], {}, {}

    for line in lines:
        tok = line.split()
        st = tok[0]
        states.append(st)

        if mtype == 'mealy':
            need = 1 + len(inputs) * 2
            if len(tok) < need:
                raise ValueError(f'row "{st}": need {need} columns, got {len(tok)}')
            for i, inp in enumerate(inputs):
                transitions[(st, inp)] = tok[1 + i]
            for i, inp in enumerate(inputs):
                outputs[(st, inp)] = tok[1 + len(inputs) + i]
        else:
            need = 1 + len(inputs) + 1
            if len(tok) < need:
                raise ValueError(f'row "{st}": need {need} columns, got {len(tok)}')
            for i, inp in enumerate(inputs):
                transitions[(st, inp)] = tok[1 + i]
            outputs[st] = tok[1 + len(inputs)]

    return states, transitions, outputs


# -----------------------------------------------------------------------
#popup window

def show_result_window(states, inputs, table, cell_display, classes, rep,
                       min_states, min_trans, min_out, ordered, log_text):

    win = tk.Toplevel()
    win.title("Minimization Result")
    win.configure(bg="#f5f4f0")
    win.resizable(True, True)

    MONO   = ("Courier New", 11)
    MONO_S = ("Courier New", 10)
    HEADER = ("Courier New", 11, "bold")
    BG     = "#f5f4f0"
    SURFACE = "#ffffff"
    BORDER  = "#c8c5be"
    CROSS_BG = "#e8e6e0"
    COMPAT_FG = "#1e6641"
    MUTED   = "#6b6860"

    tk.Label(win, text="Implication Table", font=HEADER,
             bg=BG, fg="#1a1917", pady=8).pack(anchor="w", padx=16)

    sorted_states = ordered
    n = len(sorted_states)
    CW, CH = 80, 52
    TH = 28
    LW = 30

    canvas_w = LW + CW * (n - 1) + 2
    canvas_h = TH + CH * (n - 1) + 2

    frame_tbl = tk.Frame(win, bg=BG, padx=16, pady=4)
    frame_tbl.pack(anchor="w")

    c = tk.Canvas(frame_tbl, width=canvas_w, height=canvas_h,
                  bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
    c.pack()

    for j in range(n - 1):
        x = LW + j * CW + CW // 2
        c.create_text(x, TH // 2, text=sorted_states[j], font=MONO_S, fill=MUTED)

    for i in range(1, n):
        y_top = TH + (i - 1) * CH
        c.create_text(LW // 2, y_top + CH // 2, text=sorted_states[i],
                      font=MONO_S, fill=MUTED)
        for j in range(i):
            x_left = LW + j * CW
            p = canonical(sorted_states[i], sorted_states[j])
            cell_bg = CROSS_BG if table[p] is False else SURFACE
            c.create_rectangle(x_left, y_top, x_left + CW, y_top + CH,
                                fill=cell_bg, outline=BORDER)
            label = cell_display[p]
            if table[p] is False:
                c.create_line(x_left + 4, y_top + 4,
                               x_left + CW - 4, y_top + CH - 4,
                               fill="#aaa", width=1)
                c.create_line(x_left + 4, y_top + CH - 4,
                               x_left + CW - 4, y_top + 4,
                               fill="#aaa", width=1)
                if label:
                    c.create_text(x_left + CW // 2, y_top + CH // 2,
                                  text=label, font=("Courier New", 8),
                                  fill="#aaa", justify="center")
            else:
                txt = label if label else "✓"
                fg = COMPAT_FG if not label else "#1a1917"
                c.create_text(x_left + CW // 2, y_top + CH // 2,
                               text=txt, font=("Courier New", 9),
                               fill=fg, justify="center")

    tk.Label(win, text="Equivalence Classes", font=HEADER,
             bg=BG, fg="#1a1917", pady=6).pack(anchor="w", padx=16)

    cls_frame = tk.Frame(win, bg=BG, padx=16, pady=2)
    cls_frame.pack(anchor="w")

    for cls in classes:
        r = cls[0]
        chip_text = "{" + ", ".join(cls) + "}"
        if len(cls) > 1:
            chip_text += f"  →  {r}"
        tk.Label(cls_frame, text=chip_text, font=MONO,
                 bg=SURFACE, fg="#1a1917",
                 relief="flat", bd=1,
                 padx=10, pady=4).pack(side="left", padx=4, pady=2)

    tk.Label(win, text="Step-by-step log", font=HEADER,
             bg=BG, fg="#1a1917", pady=6).pack(anchor="w", padx=16)

    log_frame = tk.Frame(win, bg=BG, padx=16, pady=4)
    log_frame.pack(fill="both", expand=True)

    log_box = scrolledtext.ScrolledText(log_frame, font=MONO_S,
                                        bg=SURFACE, fg="#1a1917",
                                        relief="flat", bd=1,
                                        wrap="none", height=18)
    log_box.pack(fill="both", expand=True)
    log_box.insert("end", log_text)
    log_box.config(state="disabled")

    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    ww = min(canvas_w + 64, sw - 80)
    wh = min(900, sh - 80)
    win.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")

EXAMPLES = {
    "e1": {
        "label": "6-state Mealy  →  4 states",
        "mtype": "mealy", "inputs": "0 1",
        "table": (
            "A  B  C  0  0\n"
            "B  D  E  0  1\n"
            "C  D  E  0  1\n"
            "D  B  F  1  0\n"
            "E  B  F  1  0\n"
            "F  D  E  1  0"
        )
    },
    "e2": {
        "label": "9-state Mealy  →  4 states",
        "mtype": "mealy", "inputs": "0 1",
        "table": (
            "a  e  e  1  1\n"
            "b  c  e  1  1\n"
            "c  i  h  0  0\n"
            "d  h  a  1  1\n"
            "e  i  e  0  0\n"
            "f  e  g  0  0\n"
            "g  h  b  1  1\n"
            "h  c  d  0  0\n"
            "i  f  b  1  1"
        )
    },
    "e3": {
        "label": "8-state Mealy  →  4 states",
        "mtype": "mealy", "inputs": "0 1",
        "table": (
            "a  h  c  1  0\n"
            "b  c  d  0  1\n"
            "c  h  b  0  0\n"
            "d  f  h  0  0\n"
            "e  c  f  0  1\n"
            "f  f  g  0  0\n"
            "g  a  c  1  0\n"
            "h  h  a  1  1"
        )
    },
    "e4": {
        "label": "5-state Moore  →  3 states",
        "mtype": "moore", "inputs": "0 1",
        "table": (
            "S0  S1  S2  0\n"
            "S1  S3  S4  0\n"
            "S2  S3  S4  0\n"
            "S3  S0  S1  1\n"
            "S4  S0  S1  1"
        )
    },
}


def main():
    root = tk.Tk()
    root.title("State Table Minimization")
    root.configure(bg="#f5f4f0")
    root.resizable(False, False)

    BG      = "#f5f4f0"
    SURFACE = "#ffffff"
    BORDER  = "#c8c5be"
    MUTED   = "#6b6860"
    TEXT    = "#1a1917"
    MONO    = ("Courier New", 11)
    SANS    = ("Segoe UI", 10) if tk.TkVersion >= 8.5 else ("Arial", 10)
    SANS_S  = ("Segoe UI", 9)  if tk.TkVersion >= 8.5 else ("Arial", 9)

    tk.Label(root, text="State Table Minimization",
             font=("Georgia", 14), bg=BG, fg=TEXT,
             pady=12).pack(anchor="w", padx=20)
    tk.Label(root, text="Implication Table Method",
             font=("Courier New", 9), bg=BG, fg=MUTED,
             pady=0).pack(anchor="w", padx=20)

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

    row1 = tk.Frame(root, bg=BG)
    row1.pack(fill="x", padx=20, pady=4)

    tk.Label(row1, text="Machine type", font=SANS_S, bg=BG, fg=MUTED).grid(row=0, column=0, sticky="w")
    tk.Label(row1, text="Input symbols", font=SANS_S, bg=BG, fg=MUTED).grid(row=0, column=1, sticky="w", padx=(20, 0))

    mtype_var = tk.StringVar(value="mealy")
    mtype_menu = tk.OptionMenu(row1, mtype_var, "mealy", "moore")
    mtype_menu.config(font=MONO, bg=SURFACE, fg=TEXT, relief="flat",
                      highlightthickness=1, highlightbackground=BORDER, width=8)
    mtype_menu["menu"].config(font=MONO, bg=SURFACE)
    mtype_menu.grid(row=1, column=0, sticky="w", pady=2)

    inputs_var = tk.StringVar(value="0 1")
    inputs_entry = tk.Entry(row1, textvariable=inputs_var, font=MONO,
                            bg=SURFACE, fg=TEXT, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER,
                            width=14)
    inputs_entry.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=2)

    tk.Label(root, text="Load example", font=SANS_S, bg=BG, fg=MUTED).pack(anchor="w", padx=20, pady=(10, 2))

    ex_frame = tk.Frame(root, bg=BG)
    ex_frame.pack(anchor="w", padx=20)

    tbl_var = tk.StringVar()

    def load_ex(key):
        ex = EXAMPLES[key]
        mtype_var.set(ex["mtype"])
        inputs_var.set(ex["inputs"])
        tbl_var.set(ex["table"])
        tbl_text.delete("1.0", "end")
        tbl_text.insert("1.0", ex["table"])
        update_hint()

    for key, ex in EXAMPLES.items():
        btn = tk.Button(ex_frame, text=ex["label"], font=SANS_S,
                        bg=SURFACE, fg=MUTED, relief="flat",
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=8, pady=4, cursor="hand2",
                        command=lambda k=key: load_ex(k))
        btn.pack(side="left", padx=(0, 6), pady=2)

    tk.Label(root, text="State table", font=SANS_S, bg=BG, fg=MUTED).pack(anchor="w", padx=20, pady=(10, 2))

    tbl_text = tk.Text(root, font=MONO, bg=SURFACE, fg=TEXT,
                       relief="flat", highlightthickness=1,
                       highlightbackground=BORDER,
                       width=52, height=10, padx=6, pady=4)
    tbl_text.pack(padx=20)

    hint_var = tk.StringVar()
    tk.Label(root, textvariable=hint_var, font=("Courier New", 9),
             bg=BG, fg=MUTED).pack(anchor="w", padx=20, pady=2)

    def update_hint(*_):
        ins = inputs_var.get().strip().split()
        m   = mtype_var.get()
        cols = (["state"] + [f"NS({i})" for i in ins] + [f"Z({i})" for i in ins]
                if m == "mealy" else
                ["state"] + [f"NS({i})" for i in ins] + ["Z"])
        hint_var.set("columns:  " + "   ".join(cols))

    mtype_var.trace_add("write", update_hint)
    inputs_var.trace_add("write", update_hint)
    update_hint()

    err_var = tk.StringVar()
    err_lbl = tk.Label(root, textvariable=err_var, font=SANS_S,
                       bg=BG, fg="#c0392b", wraplength=440)
    err_lbl.pack(anchor="w", padx=20)

    def run_minimization():
        err_var.set("")
        raw   = tbl_text.get("1.0", "end").strip()
        mtype = mtype_var.get()
        inps  = inputs_var.get().strip().split()

        if not raw:
            err_var.set("paste a state table first")
            return
        if not inps:
            err_var.set("enter at least one input symbol")
            return

        try:
            states, transitions, outputs = parse_table(raw, inps, mtype)
        except ValueError as e:
            err_var.set(str(e))
            return

        try:
            table, cell_display, classes, rep, min_states, min_trans, min_out, ordered = \
                minimize_fsm(states, inps, transitions, outputs, mtype)
        except Exception as e:
            err_var.set(f"error during minimization: {e}")
            return

        log_text = build_log(states, inps, transitions, outputs, mtype,
                             table, cell_display, classes, rep,
                             min_states, min_trans, min_out, ordered)

        show_result_window(states, inps, table, cell_display, classes, rep,
                           min_states, min_trans, min_out, ordered, log_text)

    tk.Button(root, text="▶  Run minimization",
              font=("Courier New", 11, "bold"),
              bg=TEXT, fg=SURFACE, relief="flat",
              padx=16, pady=8, cursor="hand2",
              activebackground="#333",
              command=run_minimization).pack(pady=14)

    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    ww, wh = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(sw-ww)//2}+{(sh-wh)//2}")

    root.mainloop()


if __name__ == "__main__":
    main()