import { describe, expect, it } from "vitest";
import { describeTokens } from "./avatar/sentence";
import { appendMessage, MAX_MESSAGES, signedMessage, signingSummary, typedMessage, type ChatMessage } from "./conversation";

describe("conversation messages", () => {
  it("makes a signer message only from a non-empty sentence with glosses", () => {
    expect(signedMessage(1, "  ", ["HELLO"], 0)).toBeNull();
    expect(signedMessage(1, "Hello.", [], 0)).toBeNull();
    expect(signedMessage(1, " Hello. ", ["HELLO"], 5)).toMatchObject({ from: "signer", text: "Hello.", gloss: ["HELLO"], at: 5 });
  });

  it("lists the glosses with no clip on a typed message and summarizes honestly", () => {
    const tokens = [{ gloss: "HOSPITAL", kind: "sign" }, { gloss: "WHERE", kind: "sign" }];
    const views = describeTokens(tokens, new Set(["HOSPITAL"]));
    const m = typedMessage(2, "Where is the hospital?", ["HOSPITAL", "WHERE"], views, 1, 0) as ChatMessage;
    expect(m.notSigned).toEqual(["WHERE"]);
    expect(signingSummary(m)).toBe("Signed 1 of 2. No clip for: WHERE.");
    const all = typedMessage(3, "Hello", ["HELLO"], describeTokens([{ gloss: "HELLO", kind: "sign" }], new Set(["HELLO"])), 1, 0) as ChatMessage;
    expect(signingSummary(all)).toBe("Signed all 1 sign.");
    expect(signingSummary(typedMessage(4, "xyz", [], [], 0, 0) as ChatMessage)).toBe("No signable words found.");
    expect(typedMessage(5, "   ", [], [], 0, 0)).toBeNull();
  });

  it("keeps the log bounded", () => {
    let log: ChatMessage[] = [];
    for (let i = 0; i < MAX_MESSAGES + 10; i++) log = appendMessage(log, signedMessage(i, "Hi.", ["HI"], i) as ChatMessage);
    expect(log).toHaveLength(MAX_MESSAGES);
    expect(log[0].id).toBe(10);
  });
});
