/**
 * [INPUT]: Obsidian Plugin API, CM6 extensions, sidecar AnnotationStore, anchor algorithms, views and settings modules
 * [OUTPUT]: OverlayAnnotationsPlugin main class, registers ribbon icon, commands, floating toolbar, highlights, narrow-screen popover, sidebar, settings and vault events
 * [POS]: Plugin assembly root, coordinates modules but does not modify user Markdown source
 * [PROTOCOL]: Update this header on changes, then check AGENTS.md
 */

import { addIcon, Editor, MarkdownPostProcessorContext, MarkdownView, Modal, Notice, Plugin, TFile } from "obsidian";

import { createTextAnchor, relocateDocumentAnchors } from "./src/anchor/textAnchor";
import { createHighlightExtension } from "./src/editor/highlightExtension";
import { installReadingViewHighlights, refreshReadingViewHighlights } from "./src/editor/readingViewHighlight";
import { SelectionToolbar } from "./src/editor/selectionToolbar";
import { PdfAnnotationLayer } from "./src/pdf/pdfAnnotationLayer";
import { AnnotationSettingsTab } from "./src/settings/settingsTab";
import { AnnotationStore } from "./src/storage/annotationStore";
import {
  AnnotationColor,
  AnnotationPluginSettings,
  CommentAnnotation,
  DEFAULT_SETTINGS,
  HighlightAnnotation,
  SelectionSnapshot,
} from "./src/storage/types";
import { AnnotationPopover } from "./src/views/annotationPopover";
import { ANNOTATION_SIDEBAR_VIEW, AnnotationSidebarView } from "./src/views/sidebarView";
import { StickyNoteLane } from "./src/views/stickyNoteLane";

interface CommentModalValue {
  title: string;
  content: string;
}

const NOTE_TITLE_OPTIONS = [
  { value: "Insight", label: "💡 洞见" },
  { value: "Question", label: "❓ 疑问" },
  { value: "Reminder", label: "🔔 提醒" },
] as const;

const YH_INKLIGHT_ICON = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect x="5" y="5" width="90" height="90" rx="20" ry="20" fill="#F5C518"/>
    <g transform="translate(50,50) rotate(-45) translate(-18,-18)"
      fill="none" stroke="#000" stroke-width="6"
      stroke-linecap="round" stroke-linejoin="round">
      <rect x="8" y="2" width="20" height="28" rx="3" fill="#000" stroke="none"/>
      <polygon points="8,30 28,30 18,42" fill="#000" stroke="none"/>
      <line x1="8" y1="10" x2="28" y2="10" stroke="#F5C518" stroke-width="3"/>
    </g>
  </svg>
`;

export default class OverlayAnnotationsPlugin extends Plugin {
  settings: AnnotationPluginSettings = DEFAULT_SETTINGS;
  store!: AnnotationStore;

  private toolbar!: SelectionToolbar;
  private popover!: AnnotationPopover;
  private pdfLayer!: PdfAnnotationLayer;
  private stickyLane!: StickyNoteLane;
  private lastSelection: SelectionSnapshot | null = null;
  private renameMigrationTimer: number | null = null;
  private lastBackupAt = 0;

  async onload(): Promise<void> {
    addIcon("yh-inklight-icon", YH_INKLIGHT_ICON);
    await this.loadSettings();
    this.store = new AnnotationStore(this.app);
    await this.store.initialize();
    this.registerAutomaticBackups();

    this.registerView(ANNOTATION_SIDEBAR_VIEW, (leaf) => new AnnotationSidebarView(leaf, this));
    this.registerEditorExtension([
      createHighlightExtension({
        getDocument: (filePath) => this.store.getCachedDocument(filePath),
        getVersion: () => this.store.version,
        rememberSelection: (filePath, startOffset, endOffset, selectedText) => {
          this.lastSelection = { filePath, startOffset, endOffset, selectedText };
        },
      }),
    ]);

    this.toolbar = new SelectionToolbar(this);
    this.popover = new AnnotationPopover(this);
    this.pdfLayer = new PdfAnnotationLayer(this);
    this.stickyLane = new StickyNoteLane(this);

    this.addRibbonIcon("yh-inklight-icon", "墨光批注", () => this.activateSidebarView());
    this.addSettingTab(new AnnotationSettingsTab(this));

    this.registerCommands();
    this.registerVaultEvents();

    this.registerMarkdownPostProcessor((el: HTMLElement, ctx: MarkdownPostProcessorContext) => {
      installReadingViewHighlights(el, ctx, this);
    });
  }

  async onunload(): Promise<void> {
    this.toolbar?.destroy();
    this.popover?.destroy();
    this.pdfLayer?.destroy();
    this.stickyLane?.destroy();
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  refreshAnnotations(): void {
    this.app.workspace.updateOptions();
    const activeView = this.app.workspace.getActiveViewOfType(MarkdownView);
    if (activeView) {
      refreshReadingViewHighlights(activeView.contentEl, this);
    }
    this.stickyLane?.refresh();
  }

  async activateSidebarView(): Promise<void> {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(ANNOTATION_SIDEBAR_VIEW)[0];
    if (!leaf) {
      const rightLeaf = workspace.getRightLeaf(false);
      if (rightLeaf) {
        await rightLeaf.setViewState({ type: ANNOTATION_SIDEBAR_VIEW, active: true });
        leaf = rightLeaf;
      }
    }
    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async addHighlight(color?: AnnotationColor): Promise<void> {
    if (!this.lastSelection) {
      new Notice("请先选中文本");
      return;
    }
    const { filePath, startOffset, endOffset, selectedText } = this.lastSelection;
    const anchor = createTextAnchor(startOffset, endOffset, selectedText, "", "");
    const highlight: HighlightAnnotation = {
      id: this.generateId(),
      color: color || this.settings.defaultHighlightColor,
      anchor,
      createdAt: new Date().toISOString(),
    };
    const doc = (await this.store.loadDocument(filePath)) || this.createEmptyDocument(filePath);
    doc.highlights.push(highlight);
    await this.store.saveDocument(filePath, doc);
    this.refreshAnnotations();
    this.lastSelection = null;
  }

  async addComment(color?: AnnotationColor): Promise<void> {
    if (!this.lastSelection) {
      new Notice("请先选中文本");
      return;
    }
    const modalValue = await this.showCommentModal();
    if (!modalValue) return;

    const { filePath, startOffset, endOffset, selectedText } = this.lastSelection;
    const anchor = createTextAnchor(startOffset, endOffset, selectedText, "", "");
    const comment: CommentAnnotation = {
      id: this.generateId(),
      anchor,
      title: modalValue.title,
      content: modalValue.content,
      color: color || this.settings.defaultHighlightColor,
      position: { offsetX: 0, offsetY: 0 },
      collapsed: false,
      author: this.settings.defaultAuthor,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      replies: [],
      resolved: false,
    };
    const doc = (await this.store.loadDocument(filePath)) || this.createEmptyDocument(filePath);
    doc.comments.push(comment);
    await this.store.saveDocument(filePath, doc);
    this.refreshAnnotations();
    this.lastSelection = null;
  }

  private registerCommands(): void {
    this.addCommand({
      id: "toggle-sidebar",
      name: "打开/关闭侧边栏",
      callback: () => this.activateSidebarView(),
    });

    this.addCommand({
      id: "add-highlight",
      name: "添加高亮",
      editorCallback: () => this.addHighlight(),
    });

    this.addCommand({
      id: "add-comment",
      name: "添加批注",
      editorCallback: () => this.addComment(),
    });

    this.addCommand({
      id: "toggle-sticky-notes",
      name: "显示/隐藏便签",
      hotkeys: [{ modifiers: ["Mod", "Shift"], key: "n" }],
      callback: async () => {
        this.settings.stickyNotesVisible = !this.settings.stickyNotesVisible;
        await this.saveSettings();
        this.refreshAnnotations();
      },
    });

    this.addCommand({
      id: "export-annotations",
      name: "导出批注",
      callback: async () => {
        const exported = await this.store.exportAnnotations("summary");
        if (!exported) {
          new Notice("没有可导出的批注");
          return;
        }
        await this.app.vault.create(
          `annotations-export-${new Date().toISOString().slice(0, 10)}.md`,
          exported,
        );
        new Notice("批注已导出");
      },
    });
  }

  private registerVaultEvents(): void {
    this.registerEvent(
      this.app.vault.on("rename", (file, oldPath) => {
        if (!this.settings.migrateOnRename) return;
        if (!(file instanceof TFile)) return;
        if (this.renameMigrationTimer !== null) {
          window.clearTimeout(this.renameMigrationTimer);
        }
        this.renameMigrationTimer = window.setTimeout(async () => {
          await this.store.migrateDocument(oldPath, file.path);
          this.refreshAnnotations();
          this.renameMigrationTimer = null;
        }, 500);
      }),
    );

    this.registerEvent(
      this.app.vault.on("delete", (file) => {
        if (file instanceof TFile) {
          void this.store.deleteDocument(file.path);
        }
      }),
    );
  }

  private registerAutomaticBackups(): void {
    this.registerInterval(
      window.setInterval(() => {
        void this.runScheduledBackup();
      }, 60_000),
    );
  }

  private async runScheduledBackup(): Promise<void> {
    const intervalMs = Math.max(1, this.settings.backupFrequencyMinutes) * 60_000;
    const now = Date.now();
    if (now - this.lastBackupAt < intervalMs) {
      return;
    }

    try {
      await this.store.backupDocuments();
      this.lastBackupAt = now;
    } catch (err) {
      console.error("[yh-inklight] Backup failed:", err);
    }
  }

  private createEmptyDocument(filePath: string): FileAnnotationDocument {
    return {
      filePath,
      fileHash: "",
      lastModified: new Date().toISOString(),
      highlights: [],
      comments: [],
      pdfHighlights: [],
      pdfComments: [],
    };
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  private async showCommentModal(): Promise<CommentModalValue | null> {
    return new Promise((resolve) => {
      const modal = new CommentInputModal(this.app, resolve);
      modal.open();
    });
  }
}

class CommentInputModal extends Modal {
  private resolvePromise: (value: CommentModalValue | null) => void;
  private title = "";
  private content = "";

  constructor(app: App, resolve: (value: CommentModalValue | null) => void) {
    super(app);
    this.resolvePromise = resolve;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "添加批注" });

    const titleInput = contentEl.createEl("input", {
      attr: { type: "text", placeholder: "标题（可选）" },
    });
    titleInput.addEventListener("input", () => {
      this.title = titleInput.value;
    });

    const contentInput = contentEl.createEl("textarea", {
      attr: { placeholder: "批注内容", rows: "4" },
    });
    contentInput.addEventListener("input", () => {
      this.content = contentInput.value;
    });

    const submitBtn = contentEl.createEl("button", { text: "确定" });
    submitBtn.addEventListener("click", () => {
      this.resolvePromise({ title: this.title, content: this.content });
      this.close();
    });
  }

  onClose(): void {
    this.resolvePromise(null);
  }
}
