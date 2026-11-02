import { describe, expect, it } from "vitest";
import { actionForKey, shortcutHelp } from "./shortcuts";

describe("keyboard shortcuts", () => {
  it("maps single keys to actions, case insensitive", () => {
    expect(actionForKey({ key: "r" })).toBe("record");
    expect(actionForKey({ key: "P" })).toBe("play");
    expect(actionForKey({ key: "a" })).toBe("replay");
    expect(actionForKey({ key: "u" })).toBe("undo");
    expect(actionForKey({ key: "c" })).toBe("clear");
    expect(actionForKey({ key: "s" })).toBe("send");
    expect(actionForKey({ key: "x" })).toBeNull();
  });

  it("never fires while typing or with browser modifiers", () => {
    expect(actionForKey({ key: "r", targetTag: "INPUT" })).toBeNull();
    expect(actionForKey({ key: "r", targetTag: "textarea" })).toBeNull();
    expect(actionForKey({ key: "r", targetTag: "SELECT" })).toBeNull();
    expect(actionForKey({ key: "r", editable: true })).toBeNull();
    expect(actionForKey({ key: "r", ctrlKey: true })).toBeNull();
    expect(actionForKey({ key: "p", metaKey: true })).toBeNull();
    expect(actionForKey({ key: "r", targetTag: "BUTTON" })).toBe("record");
  });

  it("describes the shortcuts a panel supports", () => {
    expect(shortcutHelp(["record", "play"])).toBe("R record, P play or pause");
  });
});
