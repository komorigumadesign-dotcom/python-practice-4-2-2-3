"""CSV集計 + 円グラフ表示 + PNGダウンロード (tkinter / matplotlib)

使い方:
  python aggregate_app.py
  1. 「ファイル選択」でCSV(名前,所属,スコア)を読み込む
  2. 「集計」ボタンで円グラフを表示
  3. 「ダウンロード」ボタンでPNG保存
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import font_manager
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import matplotlib.ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DEFAULT_CSV = Path(__file__).with_name("課題3.csv")
REQUIRED_COLUMNS = ["名前", "所属", "スコア"]
FONT_SCALE = 2  # フォントサイズ 200%
LABEL_SCALE = 1  # 棒の数値ラベル・名前目盛りの倍率(100%)
PASTEL = [matplotlib.colormaps["Pastel1"](i) for i in range(9)] +          [matplotlib.colormaps["Pastel2"](i) for i in range(8)]
LINE_COLORS = {"平均スコア": "#7FC8A9", "最高点": "#F28B82", "最低点": "#8AB4F8"}  # パステル系


def setup_japanese_font():
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Meiryo", "Yu Gothic", "MS Gothic", "Hiragino Sans", "Noto Sans CJK JP", "IPAexGothic"]:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.size"] = 10 * FONT_SCALE


def read_csv(path):
    for enc in ("utf-8-sig", "cp932"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("文字コードを判別できません (UTF-8 / Shift_JIS 以外)")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"必要な列がありません: {', '.join(missing)}")
    return df[REQUIRED_COLUMNS]


def aggregate(df):
    """所属ごとの参加者数を返す (Series)"""
    return df.groupby("所属")["名前"].count().sort_values(ascending=False)


def color_map(affiliations):
    return {a: PASTEL[i % len(PASTEL)] for i, a in enumerate(affiliations)}


def build_figure(counts, fig=None):
    """円グラフ: 所属ごとの参加者割合(参加者数)"""
    fig = fig or Figure(figsize=(7, 6), dpi=100)
    fig.clear()
    labels = list(counts.index)
    cmap = color_map(labels)
    colors = [cmap[a] for a in labels]
    total = int(counts.sum())

    ax = fig.add_subplot(111)
    ax.pie(counts, labels=labels, colors=colors, startangle=90, counterclock=False,
           autopct=lambda p: f"{p:.1f}%\n({round(p * total / 100)}人)", pctdistance=0.7,
           wedgeprops={"edgecolor": "white"}, textprops={"fontsize": 12 * FONT_SCALE})
    ax.set_title(f"「所属」ごとの参加者割合(参加者数)  合計 {total}人", fontsize=28)
    fig.tight_layout()
    return fig


METRICS = {"平均スコア": "mean", "最高点": "max", "最低点": "min"}


def score_stats(df, key, metric):
    """key('名前' or '所属')ごとにスコアを集計する (Series)"""
    return df.groupby(key, sort=False)["スコア"].agg(METRICS[metric])


def build_bar_figure(df, fig=None):
    """棒グラフ2つ: ①参加者ごと ②所属ごと(平均・最高・最低)"""
    fig = fig or Figure(figsize=(10, 8), dpi=100)
    fig.clear()
    df = df.dropna(subset=["所属", "スコア"])
    affs = list(dict.fromkeys(df["所属"]))
    cmap = color_map(sorted(affs))
    ymax = df["スコア"].max() * 1.15
    legend = [Patch(color=cmap[a], label=a) for a in sorted(affs)]

    # ① 参加者ごと: 所属ごとにまとめて並べ、全体の平均/最高/最低を点線で全て表示
    ax1 = fig.add_subplot(211)
    by_name = df.groupby("名前", sort=False)["スコア"].mean()  # 同名が複数行なら平均
    name_aff = df.drop_duplicates("名前").set_index("名前")["所属"]
    order = sorted(by_name.index, key=lambda n: (sorted(affs).index(name_aff[n]), -by_name[n]))
    by_name = by_name[order]
    bars = ax1.bar(by_name.index, by_name.values, color=[cmap[name_aff[n]] for n in by_name.index])
    ax1.bar_label(bars, labels=[f"{v:g}" for v in by_name.values], fontsize=8 * LABEL_SCALE)
    lines = []
    for label, color in tuple(LINE_COLORS.items()):
        v = df["スコア"].agg(METRICS[label])
        ax1.axhline(v, color=color, linestyle="--", linewidth=1.3)
        lines.append(Line2D([], [], color=color, linestyle="--", label=f"全体の{label}: {v:.1f}"))
    ax1.set_title("①参加者ごとのスコア(所属別に表示)", fontsize=26)
    ax1.set_xlabel("名前")
    ax1.set_ylabel("スコア")
    ax1.set_ylim(0, ymax)
    ax1.tick_params(axis="x", labelrotation=90, labelsize=8 * LABEL_SCALE)
    ax1.legend(handles=legend + lines, title="所属 / 基準線", loc="upper left",
               bbox_to_anchor=(1.01, 1), fontsize=18)

    # ② 所属ごと: 平均スコア・最高点・最低点を並べて表示
    ax2 = fig.add_subplot(212)
    aff_list = sorted(affs)
    x = list(range(len(aff_list)))
    width = 0.26
    for i, (label, color) in enumerate(tuple(LINE_COLORS.items())):
        vals = score_stats(df, "所属", label).reindex(aff_list)
        pos = [xi + (i - 1) * width for xi in x]
        bars = ax2.bar(pos, vals.values, width, color=color, alpha=0.75, label=label)
        ax2.bar_label(bars, labels=[f"{v:.1f}" if label == "平均スコア" else f"{v:g}" for v in vals.values],
                      fontsize=9 * LABEL_SCALE)
    ax2.set_xticks(x)
    ax2.set_xticklabels(aff_list)
    ax2.set_title("②所属ごとの平均スコア・最高点・最低点", fontsize=26)
    ax2.set_xlabel("所属")
    ax2.set_ylabel("スコア")
    ax2.set_ylim(0, ymax)
    ax2.legend(title="集計項目", loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=18)

    fig.tight_layout()
    return fig


def build_hist_figure(df, fig=None, bin_width=3):
    """ヒストグラム: 全参加者のスコア分布 (ビン幅3点、平均・中央値の線つき)"""
    fig = fig or Figure(figsize=(8, 6), dpi=100)
    fig.clear()
    scores = df["スコア"].dropna()
    lo = int(scores.min() // bin_width * bin_width)
    hi = int(scores.max() // bin_width * bin_width + bin_width)
    edges = list(range(lo, hi + bin_width, bin_width))  # 最大値が最後のビンに入るよう余白を確保

    ax = fig.add_subplot(111)
    counts, _, patches = ax.hist(scores, bins=edges, color=PASTEL[1], edgecolor="white", rwidth=1.0)
    ax.bar_label(patches, labels=[f"{int(c)}人" for c in counts], fontsize=10 * LABEL_SCALE)
    mean, median = scores.mean(), scores.median()
    ax.axvline(mean, color=LINE_COLORS["最高点"], linestyle="--", linewidth=1.5, label=f"平均 {mean:.1f}")
    ax.axvline(median, color=LINE_COLORS["平均スコア"], linestyle=":", linewidth=1.5, label=f"中央値 {median:.1f}")
    ax.set_xticks(edges)
    ax.set_ylim(0, max(counts) * 1.2)
    ax.set_title(f"全参加者のスコア分布 (ビン幅{bin_width}点・{len(scores)}人)", fontsize=28)
    ax.set_xlabel("スコア")
    ax.set_ylabel("参加者数(人)")
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV集計 - 所属別グラフ")
        self.geometry("900x820")
        self.df = None        # 読み込んだデータ
        self.counts = None    # 集計結果(所属別人数)

        bar = tk.Frame(self, padx=8, pady=8)
        bar.pack(fill="x")
        tk.Button(bar, text="ファイル選択", command=self.choose_file).pack(side="left")
        self.path_var = tk.StringVar(value="(未選択)")
        tk.Label(bar, textvariable=self.path_var, anchor="w").pack(side="left", padx=8, fill="x", expand=True)
        self.agg_btn = tk.Button(bar, text="集計", width=10, command=self.run_aggregate, state="disabled")
        self.agg_btn.pack(side="left", padx=4)
        self.dl_btn = tk.Button(bar, text="ダウンロード", width=12, command=self.download, state="disabled")
        self.dl_btn.pack(side="left")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # タブ1: 円グラフ
        pie_tab = tk.Frame(self.nb)
        self.nb.add(pie_tab, text="円グラフ")
        self.pie_fig = Figure(figsize=(7, 6), dpi=100)
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=pie_tab)
        self.pie_canvas.get_tk_widget().pack(fill="both", expand=True)

        # タブ2: 棒グラフ
        bar_tab = tk.Frame(self.nb)
        self.nb.add(bar_tab, text="棒グラフ")
        self.bar_fig = Figure(figsize=(10, 8), dpi=100)
        self.bar_canvas = FigureCanvasTkAgg(self.bar_fig, master=bar_tab)
        self.bar_canvas.get_tk_widget().pack(fill="both", expand=True)

        # タブ3: ヒストグラム
        hist_tab = tk.Frame(self.nb)
        self.nb.add(hist_tab, text="ヒストグラム")
        hbar = tk.Frame(hist_tab, pady=6)
        hbar.pack(fill="x")
        tk.Label(hbar, text="ビン幅(点):").pack(side="left", padx=(8, 4))
        self.bin_var = tk.StringVar(value="3")
        entry = tk.Entry(hbar, textvariable=self.bin_var, width=6, justify="right")
        entry.pack(side="left")
        entry.bind("<Return>", lambda e: self.change_bin())
        self.bin_btn = tk.Button(hbar, text="変更", width=8, command=self.change_bin, state="disabled")
        self.bin_btn.pack(side="left", padx=6)
        self.hist_fig = Figure(figsize=(8, 6), dpi=100)
        self.hist_canvas = FigureCanvasTkAgg(self.hist_fig, master=hist_tab)
        self.hist_canvas.get_tk_widget().pack(fill="both", expand=True)

        if DEFAULT_CSV.exists():
            self.load(DEFAULT_CSV)

    def choose_file(self):
        path = filedialog.askopenfilename(title="CSVファイルを選択",
                                          filetypes=[("CSV", "*.csv"), ("すべて", "*.*")])
        if path:
            self.load(path)

    def load(self, path):
        try:
            self.df = read_csv(path)
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
            return
        self.path_var.set(f"{path}  ({len(self.df)}件)")
        self.agg_btn.config(state="normal")
        self.dl_btn.config(state="disabled")
        self.counts = None
        self.bin_btn.config(state="disabled")
        for fig, canvas in ((self.pie_fig, self.pie_canvas), (self.bar_fig, self.bar_canvas),
                            (self.hist_fig, self.hist_canvas)):
            fig.clear()
            canvas.draw()

    def run_aggregate(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("集計", "集計対象のデータがありません")
            return
        data = self.df.dropna(subset=["所属"])
        self.counts = aggregate(data)
        build_figure(self.counts, self.pie_fig)
        self.pie_canvas.draw()
        build_bar_figure(self.df, self.bar_fig)
        self.bar_canvas.draw()
        self.bin_btn.config(state="normal")
        self.change_bin()
        self.dl_btn.config(state="normal")

    def change_bin(self):
        """入力欄のビン幅でヒストグラムを再描画する"""
        if self.counts is None:
            return
        try:
            width = int(self.bin_var.get())
            if not 1 <= width <= 100:
                raise ValueError
        except ValueError:
            messagebox.showwarning("ビン幅", "ビン幅は1〜100の整数で入力してください")
            return
        build_hist_figure(self.df, self.hist_fig, width)
        self.hist_canvas.draw()

    def download(self):
        if self.counts is None:
            return
        fig, name = [(self.pie_fig, "所属別円グラフ.png"), (self.bar_fig, "スコア棒グラフ.png"),
                     (self.hist_fig, "スコア分布ヒストグラム.png")][self.nb.index(self.nb.select())]
        path = filedialog.asksaveasfilename(title="PNGを保存", defaultextension=".png",
                                            initialfile=name, filetypes=[("PNG", "*.png")])
        if path:
            fig.savefig(path, dpi=150, facecolor="white", bbox_inches="tight")
            messagebox.showinfo("ダウンロード", f"保存しました:\n{path}")


if __name__ == "__main__":
    setup_japanese_font()
    App().mainloop()
