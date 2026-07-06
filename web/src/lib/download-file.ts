export type DownloadTextFileRequest = {
  readonly content: string;
  readonly filename: string;
  readonly mimeType: string;
};

export function downloadTextFile({ content, filename, mimeType }: DownloadTextFileRequest) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
