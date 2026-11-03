# Existing System and Proposed System

## Existing approaches

Communication between a deaf signer and a hearing non-signer is supported today in four broad ways, none of which is a bidirectional, privacy-preserving, in-browser ISL tool built on an open, audited dataset.

- **Human interpreters** are accurate and understand grammar and context, but they are scarce, must be arranged in advance and are not available for everyday exchanges.
- **Written text and typing** work only if both people read and write a shared written language fluently.
- **Video recordings and dictionaries of signs** show one sign at a time. They answer "what does this sign look like" but not "what did that person just sign".
- **Research recognizers** classify isolated signs from video or landmarks and report accuracy on held-out splits of their own dataset [@li2020wlasl; @sridhar2020include; @jiang2021sam; @selvaraj2022openhands]. They typically go one way (sign to text), do not include a generator, and do not report the accuracy of the path that a user would run in a browser.

The limitations of these approaches that SignBridge addresses are the one-way direction, the missing signing output, the unreported deployment gap and the lack of an explicit "unrecognized" answer.

## Proposed system

SignBridge is a web application with a Python backend. It has two directions that meet at the gloss representation (Chapter 5).

- **Sign to English.** The browser extracts landmarks and sends only landmarks. The server recognizes isolated signs, or cuts a stream into signs and recognizes each, and builds a gloss sequence and an English sentence. Answers below the confidence threshold are reported as unrecognized.
- **English to sign.** The server converts English to gloss with an editable rule layer. The browser plays one clip per gloss on a 3D avatar and lists the words that have no clip.
- **Conversation view.** One screen with a chat log for both directions.
- **Recorder.** A tool to record new signs or signer-labelled takes as landmarks only.
- **Measurement tools.** A landmark check that compares the browser landmarks with Python MediaPipe on the same recording, and a benchmark of the browser path.

[[tab:compare]] compares the existing approaches with the proposed system on the properties that matter for this project.

Table: Comparison of existing approaches and the proposed system. {#tab:compare}
| Property | Interpreter | Typing | Sign dictionary | Research recognizers | SignBridge |
|---|---|---|---|---|---|
| Sign to text | yes | no | no | yes, isolated | yes, isolated and continuous |
| Text to sign | yes | no | one sign at a time | no | yes, with an avatar |
| Works without a person | no | yes | yes | yes | yes |
| Video stays on the user's device | not applicable | yes | yes | not usually stated | yes, only landmarks leave the browser |
| States when it cannot answer | not applicable | not applicable | not applicable | not usually | yes, UNRECOGNIZED and missing clips are listed |
| Deployment accuracy reported | not applicable | not applicable | not applicable | not usually | yes, browser path benchmark |
| Reviewed by signers | not applicable | not applicable | varies | no | no, stated as a limitation |

## Advantages and honest limits

The main advantages are the shared gloss, the privacy design, the measured and reported deployment gap and the refusal to invent output. The limits are that the system covers 262 recognizable signs and some grammar words that cannot be recognized, that no clip is signer-reviewed, that facial expression is not used, and that a new signer on a real webcam is unmeasured (Chapter 10).
