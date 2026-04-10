/** Message status indicator - shows delivery/read state */

import { Check, CheckCheck, Clock } from "lucide-react";

type MessageStatus = "sending" | "sent" | "delivered" | "error";

interface MessageStatusProps {
  status: MessageStatus;
  timestamp?: string;
}

export function MessageStatus({ status, timestamp }: MessageStatusProps) {
  const icons: Record<MessageStatus, React.ReactNode> = {
    sending: <Clock size={12} className="animate-pulse text-gray-400" />,
    sent: <Check size={12} className="text-gray-400" />,
    delivered: <CheckCheck size={12} className="text-blue-400" />,
    error: <span className="text-[10px] text-red-400">失败</span>,
  };

  return (
    <span className="flex items-center gap-1" title={timestamp}>
      {icons[status]}
    </span>
  );
}
