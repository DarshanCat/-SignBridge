/** Collects extracted frames and hands them out in chunks of at most `max` (the server accepts 1 to 300 frames per message). */
export class FrameQueue<T> {
  private items: T[] = [];

  constructor(private readonly max = 300) {}

  push(item: T): void {
    this.items.push(item);
    if (this.items.length > this.max * 4) this.items.splice(0, this.items.length - this.max * 4); // never grow without bound if the socket stalls
  }

  get size(): number {
    return this.items.length;
  }

  /** Oldest frames first, at most `max`; the rest stay queued. */
  drain(): T[] {
    return this.items.splice(0, this.max);
  }

  clear(): void {
    this.items = [];
  }
}
