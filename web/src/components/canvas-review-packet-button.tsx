import { buildQuestReviewPacketDownloadPath } from "../api/quests";
import type { Quest, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { Button, buttonClassName } from "./button";

type CanvasReviewPacketButtonProps = {
  readonly quest: Quest | null;
  readonly stages: readonly StageCard[];
};

export function CanvasReviewPacketButton({ quest, stages }: CanvasReviewPacketButtonProps) {
  const { t } = useI18n();

  if (!quest) {
    return null;
  }

  if (stages.length === 0) {
    return (
      <Button disabled size="sm" type="button" variant="secondary">
        {t("downloadReviewPacket")}
      </Button>
    );
  }

  return (
    <a
      className={buttonClassName({ size: "sm", variant: "secondary" })}
      href={buildQuestReviewPacketDownloadPath(quest.id)}
    >
      {t("downloadReviewPacket")}
    </a>
  );
}
