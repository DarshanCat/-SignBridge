# Introduction

## Problem statement

Deaf and hard-of-hearing people in India use Indian Sign Language (ISL), a visual language with its own vocabulary and grammar that is distinct from English and from American Sign Language. A hearing person who does not know ISL, and a deaf person who cannot rely on written English, often have no shared language. Tools that translate in both directions would help, but the technical problem is hard: signs must be recognized from video, English must be mapped to a sign-like structure, and the result must be shown as signing that a viewer can follow. Resources for ISL are far smaller than for languages with long research histories, and a system built on them must be honest about what it can and cannot do.

SignBridge is an end-to-end prototype of this problem. It recognizes isolated and continuous signs from a webcam, builds an English sentence from them, converts typed English to ISL gloss, and signs the gloss with a 3D avatar. It is an academic prototype, not a complete ISL translator, and every claim in this report is tied to a file in the repository or to a measured result.

## Background on Indian Sign Language

ISL is produced with the hands, the arms and the upper body, together with facial expression and head movement that carry grammatical meaning such as questions and negation. Written descriptions of signs often use a gloss: an upper-case word label for each sign, in sign order, with no grammar words that the language does not sign. A gloss sequence is not a translation and not a writing system, but it is a convenient shared representation between text and signing, and it is the central representation of this project.

Machine recognition of signs usually starts from video. A pose estimator can reduce each frame to a few dozen landmarks for the body and hands, so that a classifier works on numbers instead of pixels. This makes models small and reduces the amount of personal appearance information that is processed, which is useful for privacy. It also discards what the estimator does not capture, such as most of the face, and it makes the system depend on the estimator behaving the same way on the training videos and on a live camera.

## Aim

The aim is to build and honestly evaluate an end-to-end bidirectional ISL and English prototype that runs in a web browser, that keeps the user's video on their own machine, and that reports what it could not do instead of guessing.

## Objectives

- Extract body and hand landmarks in the browser and send only landmarks to the server.
- Process the INCLUDE dataset completely, audit it, and train and compare three sequence classifiers on its authors' predefined split.
- Serve the best classifier live, with a confidence threshold chosen on validation data and an explicit "unrecognized" answer.
- Recognize signs in a continuous stream by segmenting it from hand motion and rest.
- Convert English text to ISL gloss with an editable rule layer and convert gloss back to English heuristically.
- Retarget landmark samples to avatar clips and play them on a 3D avatar with smooth transitions, without claiming that any clip is correct ISL.
- Measure how much accuracy is lost between the dataset test split and the browser path, and test a targeted augmentation against that loss.
- Provide a recorder so that new signs and signer-labelled takes can be collected, and prepare a deployment on Vercel and Hugging Face Spaces.

## Scope and what is not claimed

In scope are isolated sign recognition for the 262 INCLUDE classes, continuous recognition with synthetic pauses tested on real INCLUDE samples, text to gloss for simple single-clause sentences, and avatar playback of unreviewed clips. Not claimed are complete natural-language translation, ISL grammar including facial markers, fingerspelling, any estimate of accuracy for a new signer on a real webcam, and the correctness of any avatar clip. Results that depend on the number of seeds or on data that has not been collected are marked as pending in red.

## Contributions

- A working bidirectional prototype with a shared gloss representation, a browser-side landmark pipeline and a production build.
- A complete processing and audit of INCLUDE (4,284 samples, 262 classes) and a comparison of a 1D CNN, a BiGRU and a Transformer under identical settings.
- A browser-path benchmark that exposes a deployment gap, including a picture-aspect error that normalization by shoulder width does not remove, and the changes made in response (aspect rescale, camera request, framing guide, size warning).
- A targeted augmentation with an exact vertical-scale transform, evaluated against the deployment gap.
- A documented list of every use of the test split and of every limitation.

## Organization of this report

Chapter 2 surveys related work and Chapter 3 compares existing and proposed systems. Chapter 4 lists the requirements and Chapter 5 describes the design. Chapter 6 describes the dataset and its preprocessing, and Chapter 7 the implementation. Chapter 8 describes the testing and Chapter 9 the results. Chapter 10 states the limitations and future work and Chapter 11 concludes. The appendices give the setup and run steps and the API reference.
