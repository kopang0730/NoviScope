import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { downloadTextFile } from "../lib/download-file";
import { buildQuestReviewPacket } from "../lib/quest-review-export";
import { Button } from "./button";

type CanvasReviewPacketButtonProps = {
  readonly quest: Quest | null;
  readonly stages: readonly StageCard[];
};

function downloadQuestReviewPacket(quest: Quest, stages: readonly StageCard[]) {
  const packet = buildQuestReviewPacket(quest, stages);
  downloadTextFile({
    content: packet.content,
    filename: packet.filename,
    mimeType: "text/markdown;charset=utf-8",
  });
}

export function CanvasReviewPacketButton({ quest, stages }: CanvasReviewPacketButtonProps) {
  const { t } = useI18n();

  if (!quest) {
    return null;
  }

  return (
    <Button
      disabled={stages.length === 0}
      onClick={() => downloadQuestReviewPacket(quest, stages)}
      size="sm"
      type="button"
      variant="secondary"
    >
      {t("downloadReviewPacket")}
    </Button>
  );
}
