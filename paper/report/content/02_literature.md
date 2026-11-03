# Literature Survey

This chapter surveys the work that this project builds on. It uses only the references of the accompanying paper; each of them is still marked for checking in `paper/refs.bib` before submission, and this report inherits that status.

## Sign language datasets and recognition

Word-level datasets turned isolated sign classification into a standard benchmark. WLASL provides a large American Sign Language collection [@li2020wlasl], and INCLUDE provides a word-level collection for Indian Sign Language that is the basis of this project [@sridhar2020include]. Surveys describe the field of sign language recognition and its deep learning methods [@rastgoo2021survey]. Skeleton-based and landmark-based methods are among the strongest and cheapest systems [@jiang2021sam]. OpenHands collects pose-based models and pretrained encoders across several sign languages, including INCLUDE [@selvaraj2022openhands]. The figures it reports for INCLUDE are not repeated here because they have not been checked against the published version; Section 9.6 only compares the order of magnitude.

Two more recent resources show where the field is going. ASL Citizen is a community-sourced isolated sign dataset whose recorders are identified, which allows signer-disjoint splits [@desai2023aslcitizen]. The 2023 Google Isolated Sign Language Recognition competition on Kaggle made landmark-based isolated sign recognition an open benchmark [@kaggle2023islr]. INCLUDE has no signer identifiers, which is the root of the main limitation of this project.

All of these works evaluate on held-out splits of the same collection. This project additionally evaluates the path that a user would run.

## Landmark extraction

MediaPipe provides body pose and hand landmarks in real time on commodity hardware and in the browser [@lugaresi2019mediapipe; @bazarevsky2020blazepose; @zhang2020mediapipehands]. SignBridge uses MediaPipe Holistic unchanged on both sides of its comparison, in Python for the dataset and as a WebAssembly build in the browser, and measures how much of the observed gap is the extractor and how much is the input.

## Sequence models

Three families of sequence classifiers are compared in this project: a one-dimensional temporal convolutional network, a bidirectional gated recurrent unit network [@cho2014gru; @schuster1997birnn] and a Transformer encoder [@vaswani2017attention]. All three read a fixed-length sequence of 225 normalized landmark values per frame.

## Dataset shift, robustness and augmentation

A mismatch between training and use is a long-studied problem [@quinonero2009dataset; @torralba2011bias]. Modern benchmarks cover distribution shift in the wild [@koh2021wilds] and corruption robustness [@hendrycks2019robustness], and equally accurate models can behave differently under shift [@damour2022underspecification]. The shifts studied here are specific and physical: picture aspect, signer size in the picture and detector dropout. This allows them to be measured one at a time and an augmentation to be chosen from the measurements instead of from convention [@shorten2019augmentation].

## Abstention and calibration

A reject option trades coverage for accuracy [@geifman2017selective] and depends on confidence being meaningful, which deep networks do not guarantee [@guo2017calibration]. The live recognizer answers UNRECOGNIZED below a threshold chosen on validation data, and this report shows the coverage and accuracy trade-off per condition.

## Statistics used

Proportions are reported with Wilson score intervals [@wilson1927]. Differences between paired runs on the same videos use the exact McNemar test [@mcnemar1947] and paired bootstrap intervals [@efron1979bootstrap].

## Sign language technology with Deaf communities

Technology that claims to translate sign language has to be developed and evaluated with signers and their communities [@bragg2019interdisciplinary]. This project could not do that within its scope, and Chapter 10 states what that implies for every result.

## Gap addressed by this project

The surveyed work trains and evaluates recognizers on dataset splits. What it does not usually report is the accuracy of the complete path that a user runs in a browser, the sensitivity of that path to the camera and framing, and the product behavior that follows from such measurements. SignBridge adds this measurement, the targeted response to it, and a bidirectional prototype around it.
