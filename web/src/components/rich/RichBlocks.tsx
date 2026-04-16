import type { RichBlock } from "../../types/rich";
import { CardBlockView } from "./CardBlock";
import { DiffBlockView } from "./DiffBlock";
import { ChecklistBlockView } from "./ChecklistBlock";
import { MediaBlockView } from "./MediaBlock";
import { InteractiveBlockView } from "./InteractiveBlock";
import { AudioBlockView } from "./AudioBlock";

export function RichBlocks({ blocks }: { blocks: RichBlock[] }) {
  if (!blocks || blocks.length === 0) return null;

  return (
    <div className="mt-2 space-y-2">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "card":
            return <CardBlockView key={i} block={block} />;
          case "diff":
            return <DiffBlockView key={i} block={block} />;
          case "checklist":
            return <ChecklistBlockView key={i} block={block} />;
          case "media":
            return <MediaBlockView key={i} block={block} />;
          case "interactive":
            return <InteractiveBlockView key={i} block={block} />;
          case "audio":
            return <AudioBlockView key={i} block={block} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
