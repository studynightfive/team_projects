export interface PreparedFileSave {
  save(blob: Blob, responseFilename?: string): Promise<void>;
}

interface FilePickerWritable {
  write(data: Blob): Promise<void>;
  close(): Promise<void>;
  abort?: () => Promise<void>;
}

interface FilePickerHandle {
  createWritable(): Promise<FilePickerWritable>;
}

interface FilePickerType {
  readonly description: string;
  readonly accept: Readonly<Record<string, readonly string[]>>;
}

interface FilePickerOptions {
  readonly suggestedName: string;
  readonly types: readonly FilePickerType[];
  readonly excludeAcceptAllOption: boolean;
}

type ShowSaveFilePicker = (
  options: FilePickerOptions,
) => Promise<FilePickerHandle>;

type FilePickerWindow = Window & {
  readonly showSaveFilePicker?: ShowSaveFilePicker;
};

export interface FileSaveOptions {
  readonly suggestedName: string;
  readonly description: string;
  readonly mediaType: string;
  readonly extensions: readonly string[];
}

const triggerStandardDownload = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
};

export const prepareFileSave = async (
  options: FileSaveOptions,
): Promise<PreparedFileSave | undefined> => {
  const picker = (window as FilePickerWindow).showSaveFilePicker;
  if (picker === undefined) {
    return {
      save: (blob, responseFilename) => {
        triggerStandardDownload(
          blob,
          responseFilename?.trim() || options.suggestedName,
        );
        return Promise.resolve();
      },
    };
  }

  let handle: FilePickerHandle;
  try {
    handle = await picker({
      suggestedName: options.suggestedName,
      types: [
        {
          description: options.description,
          accept: { [options.mediaType]: options.extensions },
        },
      ],
      excludeAcceptAllOption: true,
    });
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return undefined;
    }
    throw error;
  }

  return {
    save: async (blob) => {
      const writable = await handle.createWritable();
      try {
        await writable.write(blob);
        await writable.close();
      } catch (error: unknown) {
        await writable.abort?.();
        throw error;
      }
    },
  };
};
