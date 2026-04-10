import { z } from 'zod';

export const callbackAuthSchema = z.object({
  invocationId: z.string().min(1),
  callbackToken: z.string().min(1),
});
