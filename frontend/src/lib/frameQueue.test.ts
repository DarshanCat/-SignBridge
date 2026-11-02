import { describe, expect, it } from "vitest";
import { FrameQueue } from "./frameQueue";

describe("FrameQueue", () => {
  it("drains oldest first in chunks of at most max and keeps the rest", () => {
    const q = new FrameQueue<number>(3);
    [1, 2, 3, 4, 5].forEach((n) => q.push(n));
    expect(q.drain()).toEqual([1, 2, 3]);
    expect(q.size).toBe(2);
    expect(q.drain()).toEqual([4, 5]);
    expect(q.drain()).toEqual([]);
  });

  it("is bounded when nobody drains it", () => {
    const q = new FrameQueue<number>(2);
    for (let i = 0; i < 100; i++) q.push(i);
    expect(q.size).toBe(8);
    expect(q.drain()).toEqual([92, 93]);
    q.clear();
    expect(q.size).toBe(0);
  });
});
