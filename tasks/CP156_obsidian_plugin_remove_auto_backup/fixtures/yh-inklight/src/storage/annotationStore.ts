/**
 * [INPUT]: Obsidian App/Vault/Adapter file read/write, storage/types sidecar JSON contract
 * [OUTPUT]: AnnotationStore for Markdown/PDF .obsidian-annotations sidecar files, index, cache and export
 * [POS]: storage module's sole persistence entry, isolates original Markdown from annotation data
 * [PROTOCOL]: Update this header on changes, then check AGENTS.md
 */

import { App, normalizePath, Notice, TFile } from "obsidian";

import {
  AnnotationIndex,
  AnnotationIndexEntry,
  AnnotationColor,
  AnnotationExportFormat,
  CommentAnnotation,
  EMPTY_INDEX,
  FileAnnotationDocument,
  HighlightAnnotation,
  PdfCommentAnnotation,
  PdfHighlightAnnotation,
} from "./types";

const STORE_DIR = ".obsidian-annotations";
const INDEX_PATH = normalizePath(`${STORE_DIR}/index.json`);
const BACKUP_DIR = normalizePath(`${STORE_DIR}/backups`);
const MAX_LEGACY_SIDECAR_NAME_LENGTH = 180;
const MAX_COMPACT_SIDECAR_PREFIX_LENGTH = 96;

interface ExportDocumentSource {
  filePath: string;
  document: FileAnnotationDocument;
}

interface ExportEntry {
  kind: "highlight" | "note";
  mode: "md" | "pdf";
  sourcePath: string;
  color: AnnotationColor;
  text: string;
  content: string;
  createdAt: string;
  pageNumber: number | null;
  startOffset: number;
}

export class AnnotationStoreReadError extends Error {
  constructor(readonly path: string, readonly originalError: unknown) {
    super(`Failed to read annotation sidecar JSON: ${path}`);
    this.name = "AnnotationStoreReadError";
  }
}

export class AnnotationStoreWriteError extends Error {
  constructor(readonly path: string, readonly originalError: unknown) {
    super(`Failed to write annotation sidecar JSON: ${path}`);
    this.name = "AnnotationStoreWriteError";
  }
}

export class AnnotationStore {
  private readonly documents = new Map<string, FileAnnotationDocument>();
  private index: AnnotationIndex = EMPTY_INDEX;
  private _version = 0;

  get version(): number {
    return this._version;
  }

  constructor(private readonly app: App) {}

  async initialize(): Promise<void> {
    await this.ensureStoreDir();
    await this.loadIndex();
  }

  getCachedDocument(filePath: string): FileAnnotationDocument | undefined {
    return this.documents.get(filePath);
  }

  async loadDocument(filePath: string): Promise<FileAnnotationDocument | null> {
    const sidecarPath = this.getSidecarPath(filePath);
    try {
      const raw = await this.app.vault.adapter.read(sidecarPath);
      const doc: FileAnnotationDocument = JSON.parse(raw);
      this.documents.set(filePath, doc);
      return doc;
    } catch {
      return null;
    }
  }

  async saveDocument(filePath: string, doc: FileAnnotationDocument): Promise<void> {
    const sidecarPath = this.getSidecarPath(filePath);
    await this.ensureStoreDir();
    try {
      await this.app.vault.adapter.write(sidecarPath, JSON.stringify(doc, null, 2));
      this.documents.set(filePath, doc);
      this._version++;
      await this.updateIndex(filePath, sidecarPath, doc);
    } catch (err) {
      throw new AnnotationStoreWriteError(sidecarPath, err);
    }
  }

  async deleteDocument(filePath: string): Promise<void> {
    const sidecarPath = this.getSidecarPath(filePath);
    try {
      await this.app.vault.adapter.remove(sidecarPath);
    } catch {
      // File may not exist
    }
    this.documents.delete(filePath);
    delete this.index.files[filePath];
    await this.saveIndex();
    this._version++;
  }

  async migrateDocument(oldPath: string, newPath: string): Promise<void> {
    const doc = await this.loadDocument(oldPath);
    if (!doc) return;
    doc.filePath = newPath;
    await this.saveDocument(newPath, doc);
    await this.deleteDocument(oldPath);
  }

  async exportAnnotations(format: AnnotationExportFormat): Promise<string> {
    const sources: ExportDocumentSource[] = [];
    for (const [filePath, doc] of this.documents) {
      sources.push({ filePath, document: doc });
    }
    const entries = this.collectExportEntries(sources);
    return this.formatExport(entries, format);
  }

  async backupDocuments(): Promise<number> {
    await this.ensureStoreDir();
    await this.ensureDir(BACKUP_DIR);

    const listed = await this.app.vault.adapter.list(STORE_DIR);
    const sidecars = listed.files.filter((path: string) => {
      const normalizedPath = normalizePath(path);
      return (
        normalizedPath.endsWith(".json") &&
        normalizedPath !== INDEX_PATH &&
        !normalizedPath.startsWith(`${BACKUP_DIR}/`)
      );
    });

    if (!sidecars.length) {
      return 0;
    }

    const snapshotDir = normalizePath(`${BACKUP_DIR}/${backupTimestamp()}`);
    await this.ensureDir(snapshotDir);

    for (const sidecar of sidecars) {
      const content = await this.app.vault.adapter.read(sidecar);
      const target = normalizePath(`${snapshotDir}/${sidecar.split("/").pop()}`);
      await this.app.vault.adapter.write(target, content);
    }

    return sidecars.length;
  }

  private getSidecarPath(filePath: string): string {
    const safeFileName = filePath
      .replace(/[/\\]/g, "_")
      .replace(/\.\w+$/, "")
      .slice(0, MAX_COMPACT_SIDECAR_PREFIX_LENGTH);
    return normalizePath(`${STORE_DIR}/${safeFileName}.json`);
  }

  private async ensureStoreDir(): Promise<void> {
    await this.ensureDir(STORE_DIR);
  }

  private async ensureDir(dir: string): Promise<void> {
    if (!(await this.app.vault.adapter.exists(dir))) {
      await this.app.vault.adapter.mkdir(dir);
    }
  }

  private async loadIndex(): Promise<void> {
    try {
      const raw = await this.app.vault.adapter.read(INDEX_PATH);
      this.index = JSON.parse(raw);
    } catch {
      this.index = { ...EMPTY_INDEX };
    }
  }

  private async saveIndex(): Promise<void> {
    await this.app.vault.adapter.write(INDEX_PATH, JSON.stringify(this.index, null, 2));
  }

  private async updateIndex(
    filePath: string,
    sidecarPath: string,
    doc: FileAnnotationDocument,
  ): Promise<void> {
    this.index.files[filePath] = {
      filePath,
      sidecarPath,
      fileHash: doc.fileHash,
      highlightCount: doc.highlights.length + doc.pdfHighlights.length,
      commentCount: doc.comments.length + doc.pdfComments.length,
      updatedAt: doc.lastModified,
    };
    await this.saveIndex();
  }

  private collectExportEntries(sources: ExportDocumentSource[]): ExportEntry[] {
    const entries: ExportEntry[] = [];
    for (const { filePath, document: doc } of sources) {
      for (const h of doc.highlights) {
        entries.push({
          kind: "highlight",
          mode: "md",
          sourcePath: filePath,
          color: h.color,
          text: h.anchor.selectedText,
          content: "",
          createdAt: h.createdAt,
          pageNumber: null,
          startOffset: h.anchor.startOffset,
        });
      }
      for (const c of doc.comments) {
        entries.push({
          kind: "note",
          mode: "md",
          sourcePath: filePath,
          color: c.color,
          text: c.anchor.selectedText,
          content: c.content,
          createdAt: c.createdAt,
          pageNumber: null,
          startOffset: c.anchor.startOffset,
        });
      }
    }
    return entries;
  }

  private formatExport(entries: ExportEntry[], format: AnnotationExportFormat): string {
    if (format === "summary") {
      return entries.map((e) => `- [${e.color}] ${e.text}`).join("\n");
    }
    if (format === "notes-only") {
      return entries
        .filter((e) => e.kind === "note")
        .map((e) => `> ${e.text}\n\n${e.content}`)
        .join("\n\n---\n\n");
    }
    return entries.map((e) => `[${e.color}] ${e.text}: ${e.content}`).join("\n");
  }
}

function backupTimestamp(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}
