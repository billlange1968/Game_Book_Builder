"""
Game Book Story Builder
========================================
A GUI application for creating branching stories and exporting them as PDFs.

Requirements:
    pip install reportlab

Run:
    python game_book_builder.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import random
import os
from copy import deepcopy

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# ─────────────────────────────────────────────────────────────
#  Data model
# ─────────────────────────────────────────────────────────────

class StoryNode:
    """Represents one passage / page in the adventure."""

    def __init__(self, node_id: str, title: str = "", content: str = ""):
        self.node_id: str = node_id
        self.title: str = title
        self.content: str = content
        # list of {"text": "...", "target_id": "..."} dicts
        self.choices: list[dict] = []
        # assigned page number (set during PDF generation)
        self.page_num: int = 0

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "content": self.content,
            "choices": self.choices,
        }

    @staticmethod
    def from_dict(d: dict) -> "StoryNode":
        n = StoryNode(d["node_id"], d.get("title", ""), d.get("content", ""))
        n.choices = d.get("choices", [])
        return n


class Story:
    """Container for all nodes and metadata."""

    def __init__(self):
        self.title: str = "My Adventure"
        self.author: str = ""
        self.start_node_id: str = ""
        self.nodes: dict[str, StoryNode] = {}

    def add_node(self, node: StoryNode):
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str):
        self.nodes.pop(node_id, None)
        for n in self.nodes.values():
            n.choices = [c for c in n.choices if c["target_id"] != node_id]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "start_node_id": self.start_node_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    @staticmethod
    def from_dict(d: dict) -> "Story":
        s = Story()
        s.title = d.get("title", "My Adventure")
        s.author = d.get("author", "")
        s.start_node_id = d.get("start_node_id", "")
        for k, v in d.get("nodes", {}).items():
            s.nodes[k] = StoryNode.from_dict(v)
        return s


# ─────────────────────────────────────────────────────────────
#  PDF generator
# ─────────────────────────────────────────────────────────────

def generate_pdf(story: Story, output_path: str, randomize: bool = True):
    """Render the story to a PDF, optionally shuffling passage order."""

    if not REPORTLAB_OK:
        raise ImportError("reportlab is not installed. Run: pip install reportlab")

    # ── Assign page numbers ──────────────────────────────────
    node_list = list(story.nodes.values())
    if not node_list:
        raise ValueError("Story has no nodes.")

    # Always put the start node on page 1 if it exists
    start = story.nodes.get(story.start_node_id)
    others = [n for n in node_list if n.node_id != story.start_node_id]

    if randomize:
        random.shuffle(others)

    ordered = ([start] if start else []) + others

    # Assign page numbers (1-based)
    for i, node in enumerate(ordered):
        node.page_num = i + 1

    page_map = {n.node_id: n.page_num for n in ordered}

    # ── Build PDF ────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=1.1 * inch,
        rightMargin=1.1 * inch,
        topMargin=1.1 * inch,
        bottomMargin=1.1 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=14,
        alignment=TA_CENTER,
    )
    author_style = ParagraphStyle(
        "CoverAuthor",
        parent=styles["Normal"],
        fontSize=14,
        textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    page_header_style = ParagraphStyle(
        "PageHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=0,
        spaceAfter=6,
    )
    passage_num_style = ParagraphStyle(
        "PassageNum",
        parent=styles["Normal"],
        fontSize=22,
        textColor=colors.HexColor("#c0392b"),
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=17,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )
    choice_header_style = ParagraphStyle(
        "ChoiceHeader",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#888888"),
        spaceBefore=10,
        spaceAfter=2,
        fontName="Helvetica-Oblique",
    )
    choice_style = ParagraphStyle(
        "Choice",
        parent=styles["Normal"],
        fontSize=11,
        leftIndent=18,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1a2e"),
    )
    ending_style = ParagraphStyle(
        "Ending",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique",
        spaceAfter=6,
    )

    elements = []

    # ── Cover page ───────────────────────────────────────────
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(story.title or "Untitled Adventure", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#c0392b"), spaceAfter=16))
    if story.author:
        elements.append(Paragraph(f"by {story.author}", author_style))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph(
            "This is a Choose Your Own Adventure story. "
            "Begin at <b>Passage 1</b>. "
            "At the end of each passage, follow the instructions to continue your journey.",
            ParagraphStyle("Intro", parent=styles["Normal"], fontSize=11,
                           alignment=TA_CENTER, textColor=colors.HexColor("#555555")),
        )
    )
    elements.append(PageBreak())

    # ── Passages ─────────────────────────────────────────────
    for node in ordered:
        # Big centred passage number
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(str(node.page_num), passage_num_style))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor("#cccccc"), spaceAfter=10))

        # Optional title
        if node.title.strip():
            elements.append(Paragraph(node.title, page_header_style))

        # Body text – split on blank lines into separate paragraphs
        paragraphs = [p.strip() for p in node.content.split("\n\n") if p.strip()]
        for para in paragraphs:
            # Replace single newlines with spaces for clean flow
            para = para.replace("\n", " ")
            elements.append(Paragraph(para, body_style))

        # Choices
        if node.choices:
            elements.append(Paragraph("Your choices:", choice_header_style))
            for choice in node.choices:
                target_page = page_map.get(choice["target_id"], "?")
                arrow = "&#x2794;"   # ➔  (HTML entity)
                elements.append(
                    Paragraph(
                        f"{arrow} {choice['text']}  "
                        f"<font color='#c0392b'><b>&#8594; Turn to passage {target_page}</b></font>",
                        choice_style,
                    )
                )
        else:
            elements.append(Paragraph("— The End —", ending_style))

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(PageBreak())

    doc.build(elements)
    return page_map


# ─────────────────────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────────────────────

class App(tk.Tk):

    # ── Init ─────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.title("Choose Your Own Adventure Builder")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg="#f5f5f5")

        self.story = Story()
        self._node_counter = 0
        self._current_node_id: str | None = None

        self._build_menu()
        self._build_ui()

        # Start with a default opening node
        self._new_node(title="Opening Passage",
                       content="Your adventure begins here...")
        if self.story.nodes:
            first_id = next(iter(self.story.nodes))
            self.story.start_node_id = first_id
            self._select_node(first_id)

    # ── Menu ─────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Story", command=self._menu_new)
        file_menu.add_command(label="Open…", command=self._menu_open)
        file_menu.add_command(label="Save", command=self._menu_save)
        file_menu.add_command(label="Save As…", command=self._menu_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export PDF…", command=self._menu_export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        node_menu = tk.Menu(menubar, tearoff=0)
        node_menu.add_command(label="Add Passage", command=lambda: self._new_node())
        node_menu.add_command(label="Delete Selected Passage",
                              command=self._delete_current_node)
        node_menu.add_separator()
        node_menu.add_command(label="Set as Start Passage",
                              command=self._set_as_start)
        menubar.add_cascade(label="Passages", menu=node_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to Use", command=self._show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)
        self._save_path: str | None = None

    # ── Main layout ──────────────────────────────────────────

    def _build_ui(self):
        # Top bar: story metadata
        top = tk.Frame(self, bg="#1a1a2e", pady=8, padx=12)
        top.pack(fill=tk.X)

        tk.Label(top, text="Story Title:", bg="#1a1a2e", fg="white",
                 font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.story_title_var = tk.StringVar(value="My Adventure")
        self.story_title_var.trace_add("write", lambda *_: self._sync_story_meta())
        ttk.Entry(top, textvariable=self.story_title_var, width=30).pack(
            side=tk.LEFT, padx=(4, 16))

        tk.Label(top, text="Author:", bg="#1a1a2e", fg="white",
                 font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.author_var = tk.StringVar()
        self.author_var.trace_add("write", lambda *_: self._sync_story_meta())
        ttk.Entry(top, textvariable=self.author_var, width=20).pack(
            side=tk.LEFT, padx=(4, 16))

        self.start_label = tk.Label(top, text="Start: (none)", bg="#1a1a2e",
                                    fg="#f39c12", font=("Helvetica", 10, "italic"))
        self.start_label.pack(side=tk.RIGHT, padx=8)

        # Main pane: left=passage list, right=editor
        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5,
                              bg="#cccccc")
        pane.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Left panel
        left = tk.Frame(pane, bg="#f0f0f0", width=220)
        pane.add(left, minsize=180)

        lbl_frame = tk.Frame(left, bg="#2c3e50", pady=6)
        lbl_frame.pack(fill=tk.X)
        tk.Label(lbl_frame, text="Passages", bg="#2c3e50", fg="white",
                 font=("Helvetica", 12, "bold")).pack(side=tk.LEFT, padx=10)
        add_btn = tk.Button(lbl_frame, text="＋", bg="#27ae60", fg="white",
                            font=("Helvetica", 12, "bold"), relief=tk.FLAT,
                            command=lambda: self._new_node(), cursor="hand2",
                            padx=6)
        add_btn.pack(side=tk.RIGHT, padx=6)

        self.node_listbox = tk.Listbox(
            left, bg="#f9f9f9", selectbackground="#1a1a2e",
            selectforeground="white", font=("Helvetica", 10),
            relief=tk.FLAT, borderwidth=0, activestyle="none",
        )
        self.node_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.node_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        del_btn = tk.Button(left, text="Delete Passage", bg="#c0392b", fg="white",
                            font=("Helvetica", 10), relief=tk.FLAT,
                            command=self._delete_current_node, cursor="hand2")
        del_btn.pack(fill=tk.X, padx=6, pady=(0, 6))

        # Right panel – editor
        right = tk.Frame(pane, bg="white")
        pane.add(right, minsize=500)

        self._build_editor(right)

    def _build_editor(self, parent):
        # Header
        hdr = tk.Frame(parent, bg="#ecf0f1", pady=8, padx=12)
        hdr.pack(fill=tk.X)

        tk.Label(hdr, text="Passage Title:", bg="#ecf0f1",
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky=tk.W)
        self.node_title_var = tk.StringVar()
        ttk.Entry(hdr, textvariable=self.node_title_var, width=40).grid(
            row=0, column=1, padx=(6, 20), sticky=tk.W)

        tk.Label(hdr, text="Passage ID:", bg="#ecf0f1",
                 font=("Helvetica", 10)).grid(row=0, column=2, sticky=tk.W)
        self.node_id_label = tk.Label(hdr, text="—", bg="#ecf0f1",
                                      font=("Courier", 10), fg="#555555")
        self.node_id_label.grid(row=0, column=3, padx=(4, 0), sticky=tk.W)

        set_start_btn = tk.Button(hdr, text="★ Set as Start",
                                  bg="#f39c12", fg="white", relief=tk.FLAT,
                                  font=("Helvetica", 10), command=self._set_as_start,
                                  cursor="hand2", padx=8)
        set_start_btn.grid(row=0, column=4, padx=(20, 0))

        # Body text
        tk.Label(parent, text="Passage Text:", bg="white",
                 font=("Helvetica", 10, "bold"), anchor=tk.W).pack(
            fill=tk.X, padx=12, pady=(8, 2))

        self.content_text = scrolledtext.ScrolledText(
            parent, height=10, font=("Georgia", 11), wrap=tk.WORD,
            relief=tk.GROOVE, borderwidth=1, padx=8, pady=8,
        )
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=4)

        # Choices section
        choices_hdr = tk.Frame(parent, bg="white")
        choices_hdr.pack(fill=tk.X, padx=12)
        tk.Label(choices_hdr, text="Choices / Branches:",
                 bg="white", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(choices_hdr, text="＋ Add Choice", bg="#2980b9", fg="white",
                  relief=tk.FLAT, font=("Helvetica", 10),
                  command=self._add_choice_row, cursor="hand2", padx=8
                  ).pack(side=tk.RIGHT)

        # Scrollable choice rows
        choice_outer = tk.Frame(parent, bg="white")
        choice_outer.pack(fill=tk.BOTH, expand=False, padx=12, pady=(4, 4))

        self.choice_canvas = tk.Canvas(choice_outer, bg="white",
                                       height=160, highlightthickness=0)
        scrollbar = ttk.Scrollbar(choice_outer, orient=tk.VERTICAL,
                                  command=self.choice_canvas.yview)
        self.choice_frame = tk.Frame(self.choice_canvas, bg="white")
        self.choice_frame.bind("<Configure>", lambda e: self.choice_canvas.configure(
            scrollregion=self.choice_canvas.bbox("all")))

        self.choice_canvas.create_window((0, 0), window=self.choice_frame,
                                         anchor=tk.NW)
        self.choice_canvas.configure(yscrollcommand=scrollbar.set)
        self.choice_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._choice_rows: list[dict] = []   # {"frame","text_var","target_var"}

        # Save button
        save_row = tk.Frame(parent, bg="white", pady=6)
        save_row.pack(fill=tk.X, padx=12)
        tk.Button(save_row, text="💾  Save Passage Changes",
                  bg="#27ae60", fg="white", font=("Helvetica", 11, "bold"),
                  relief=tk.FLAT, command=self._save_current_node,
                  cursor="hand2", padx=12, pady=6
                  ).pack(side=tk.LEFT)
        self.status_label = tk.Label(save_row, text="", bg="white",
                                     fg="#27ae60", font=("Helvetica", 10, "italic"))
        self.status_label.pack(side=tk.LEFT, padx=12)

        # Export buttons
        exp_row = tk.Frame(parent, bg="#ecf0f1", pady=8)
        exp_row.pack(fill=tk.X, padx=0)
        tk.Button(exp_row, text="📄  Export PDF (Randomized)",
                  bg="#8e44ad", fg="white", font=("Helvetica", 11, "bold"),
                  relief=tk.FLAT, command=lambda: self._menu_export_pdf(randomize=True),
                  cursor="hand2", padx=12, pady=6
                  ).pack(side=tk.LEFT, padx=12)
        tk.Button(exp_row, text="📄  Export PDF (In Order)",
                  bg="#2c3e50", fg="white", font=("Helvetica", 11, "bold"),
                  relief=tk.FLAT, command=lambda: self._menu_export_pdf(randomize=False),
                  cursor="hand2", padx=12, pady=6
                  ).pack(side=tk.LEFT)

    # ── Node list helpers ────────────────────────────────────

    def _refresh_node_list(self):
        self.node_listbox.delete(0, tk.END)
        for node_id, node in self.story.nodes.items():
            star = "★ " if node_id == self.story.start_node_id else "   "
            label = node.title.strip() or node_id
            self.node_listbox.insert(tk.END, f"{star}{label}")
        # Update start label
        start = self.story.nodes.get(self.story.start_node_id)
        if start:
            self.start_label.config(
                text=f"Start: {start.title.strip() or start.node_id}")
        else:
            self.start_label.config(text="Start: (none)")

    def _on_list_select(self, event):
        sel = self.node_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        node_id = list(self.story.nodes.keys())[idx]
        self._select_node(node_id)

    def _select_node(self, node_id: str):
        # Auto-save current before switching
        if self._current_node_id and self._current_node_id in self.story.nodes:
            self._save_current_node(silent=True)

        self._current_node_id = node_id
        node = self.story.nodes[node_id]

        self.node_title_var.set(node.title)
        self.node_id_label.config(text=node_id)

        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", node.content)

        # Rebuild choice rows
        for row in self._choice_rows:
            row["frame"].destroy()
        self._choice_rows.clear()

        for choice in node.choices:
            self._add_choice_row(choice["text"], choice["target_id"])

        # Highlight in listbox
        keys = list(self.story.nodes.keys())
        if node_id in keys:
            idx = keys.index(node_id)
            self.node_listbox.selection_clear(0, tk.END)
            self.node_listbox.selection_set(idx)
            self.node_listbox.see(idx)

    def _new_node(self, title: str = "", content: str = "") -> str:
        self._node_counter += 1
        node_id = f"node_{self._node_counter:03d}"
        node = StoryNode(node_id, title or f"Passage {self._node_counter}", content)
        self.story.add_node(node)
        if not self.story.start_node_id:
            self.story.start_node_id = node_id
        self._refresh_node_list()
        self._select_node(node_id)
        return node_id

    def _delete_current_node(self):
        if not self._current_node_id:
            return
        if len(self.story.nodes) <= 1:
            messagebox.showwarning("Cannot Delete",
                                   "You need at least one passage.")
            return
        confirm = messagebox.askyesno(
            "Delete Passage",
            f"Delete '{self._current_node_id}'? "
            "Any choices pointing to it will also be removed.")
        if not confirm:
            return
        self.story.remove_node(self._current_node_id)
        if self.story.start_node_id == self._current_node_id:
            self.story.start_node_id = next(iter(self.story.nodes), "")
        self._current_node_id = None
        self._refresh_node_list()
        if self.story.nodes:
            first_id = next(iter(self.story.nodes))
            self._select_node(first_id)

    def _set_as_start(self):
        if self._current_node_id:
            self.story.start_node_id = self._current_node_id
            self._refresh_node_list()

    # ── Choice rows ──────────────────────────────────────────

    def _add_choice_row(self, choice_text: str = "", target_id: str = ""):
        row = tk.Frame(self.choice_frame, bg="#f9f9f9",
                       pady=3, padx=4, relief=tk.GROOVE, bd=1)
        row.pack(fill=tk.X, pady=2, padx=2)

        tk.Label(row, text="Choice text:", bg="#f9f9f9",
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky=tk.W)
        text_var = tk.StringVar(value=choice_text)
        ttk.Entry(row, textvariable=text_var, width=30).grid(
            row=0, column=1, padx=(4, 10))

        tk.Label(row, text="→ Passage ID:", bg="#f9f9f9",
                 font=("Helvetica", 9)).grid(row=0, column=2, sticky=tk.W)

        target_var = tk.StringVar(value=target_id)
        combo = ttk.Combobox(row, textvariable=target_var, width=18,
                             values=list(self.story.nodes.keys()))
        combo.grid(row=0, column=3, padx=(4, 10))

        def refresh_combo(event=None):
            combo["values"] = list(self.story.nodes.keys())

        combo.bind("<ButtonPress>", refresh_combo)

        def remove():
            row.destroy()
            self._choice_rows[:] = [r for r in self._choice_rows
                                     if r["frame"].winfo_exists()]

        tk.Button(row, text="✕", bg="#c0392b", fg="white", relief=tk.FLAT,
                  font=("Helvetica", 9, "bold"), command=remove,
                  cursor="hand2").grid(row=0, column=4)

        self._choice_rows.append({"frame": row, "text_var": text_var,
                                   "target_var": target_var})

    # ── Save / sync ──────────────────────────────────────────

    def _save_current_node(self, silent: bool = False):
        if not self._current_node_id:
            return
        node = self.story.nodes.get(self._current_node_id)
        if not node:
            return

        node.title = self.node_title_var.get()
        node.content = self.content_text.get("1.0", tk.END).rstrip()

        # Rebuild choices from rows
        node.choices = []
        for row in self._choice_rows:
            if not row["frame"].winfo_exists():
                continue
            text = row["text_var"].get().strip()
            target = row["target_var"].get().strip()
            if text and target:
                node.choices.append({"text": text, "target_id": target})

        self._refresh_node_list()
        if not silent:
            self.status_label.config(text="Saved ✓")
            self.after(2000, lambda: self.status_label.config(text=""))

    def _sync_story_meta(self):
        self.story.title = self.story_title_var.get()
        self.story.author = self.author_var.get()

    # ── File menu actions ────────────────────────────────────

    def _menu_new(self):
        if not messagebox.askyesno("New Story",
                                   "Discard current story and start fresh?"):
            return
        self.story = Story()
        self._node_counter = 0
        self._current_node_id = None
        self.story_title_var.set("My Adventure")
        self.author_var.set("")
        self._save_path = None
        for row in self._choice_rows:
            row["frame"].destroy()
        self._choice_rows.clear()
        self.node_listbox.delete(0, tk.END)
        self.content_text.delete("1.0", tk.END)
        self._new_node(title="Opening Passage",
                       content="Your adventure begins here...")

    def _menu_open(self):
        path = filedialog.askopenfilename(
            title="Open Story", filetypes=[("CYOA Story", "*.cyoa"),
                                           ("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.story = Story.from_dict(data)
            # Sync counter to highest existing node number
            nums = []
            for k in self.story.nodes:
                try:
                    nums.append(int(k.split("_")[-1]))
                except ValueError:
                    pass
            self._node_counter = max(nums, default=0)
            self._save_path = path
            self.story_title_var.set(self.story.title)
            self.author_var.set(self.story.author)
            self._current_node_id = None
            self._refresh_node_list()
            if self.story.nodes:
                first = self.story.start_node_id or next(iter(self.story.nodes))
                self._select_node(first)
        except Exception as e:
            messagebox.showerror("Open Error", str(e))

    def _menu_save(self):
        if self._save_path:
            self._do_save(self._save_path)
        else:
            self._menu_save_as()

    def _menu_save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Story",
            defaultextension=".cyoa",
            filetypes=[("CYOA Story", "*.cyoa"), ("JSON", "*.json")])
        if path:
            self._do_save(path)
            self._save_path = path

    def _do_save(self, path: str):
        self._save_current_node(silent=True)
        self._sync_story_meta()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.story.to_dict(), f, indent=2)
            self.status_label.config(text=f"Saved to {os.path.basename(path)} ✓")
            self.after(3000, lambda: self.status_label.config(text=""))
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _menu_export_pdf(self, randomize: bool = True):
        if not REPORTLAB_OK:
            messagebox.showerror(
                "Missing Library",
                "reportlab is not installed.\n\nRun:\n  pip install reportlab")
            return

        self._save_current_node(silent=True)
        self._sync_story_meta()

        if not self.story.nodes:
            messagebox.showwarning("No Passages", "Add some passages first.")
            return

        path = filedialog.asksaveasfilename(
            title="Export PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if not path:
            return

        try:
            page_map = generate_pdf(self.story, path, randomize=randomize)
            summary = "\n".join(
                f"  {nid}  →  page {pg}" for nid, pg in page_map.items())
            messagebox.showinfo(
                "PDF Exported",
                f"PDF saved to:\n{path}\n\nPassage → Page mapping:\n{summary}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ── Help ─────────────────────────────────────────────────

    def _show_help(self):
        win = tk.Toplevel(self)
        win.title("How to Use")
        win.geometry("520x460")
        win.configure(bg="white")

        txt = scrolledtext.ScrolledText(win, font=("Helvetica", 11),
                                        wrap=tk.WORD, relief=tk.FLAT,
                                        bg="white", padx=16, pady=12)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, HELP_TEXT)
        txt.config(state=tk.DISABLED)


HELP_TEXT = """\
CHOOSE YOUR OWN ADVENTURE BUILDER – QUICK GUIDE
================================================

1. STORY METADATA
   Enter your story title and author name at the top.

2. PASSAGES
   • Each "passage" is one chunk of story text (like a page in a CYOA book).
   • Click [ + ] in the Passages panel to create a new one.
   • Click a passage in the list to edit it.
   • The ★ symbol marks the starting passage (the first page of the PDF).

3. WRITING A PASSAGE
   • Give it a short title (optional – used in the PDF heading).
   • Write your story text in the large box.
     Separate paragraphs with a blank line.
   • Click "Save Passage Changes" or switch passages – it auto-saves.

4. CHOICES / BRANCHES
   • Click "+ Add Choice" to add a decision the reader can make.
   • Fill in the choice text (e.g. "Open the mysterious door").
   • Select the Passage ID the choice leads to from the dropdown.
   • Passages with NO choices are treated as endings.

5. EXPORTING TO PDF
   • "Export PDF (Randomized)" – shuffles passage order so the page
     numbers are unpredictable (classic CYOA feel!). The start passage
     is always page 1.
   • "Export PDF (In Order)" – passages appear in creation order.
   • After export you'll see which passage ended up on which page.

6. SAVING / LOADING
   • File → Save / Save As to save as a .cyoa file (JSON format).
   • File → Open to reload a saved story.

TIPS
----
• Plan your story as a flowchart first – sketch nodes and arrows on paper.
• Keep passage text 100-300 words for readability.
• Test your story by tracing all paths to make sure every branch leads
  somewhere (or ends intentionally).
"""


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not REPORTLAB_OK:
        print("⚠  reportlab not found. PDF export will be disabled.")
        print("   Install it with:  pip install reportlab\n")

    app = App()
    app.mainloop()

