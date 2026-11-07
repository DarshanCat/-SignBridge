# Extra datasets: ISL-CSLTR and WLASL (investigation only)

Written 2026-11-07. Nothing was downloaded: no video, no zip, no annotation file. Everything below comes from the dataset pages, the GitHub API (file names and sizes only), one HTTP HEAD request to the ISL-CSLTR file (headers only) and the WLASL paper abstract. Where a page does not say something, this document says so instead of guessing. Authors' predefined split, signer independence not verified, still applies to every INCLUDE number; none of the proposals below changes a trained model or an evaluation result.

## 1. ISL-CSLTR (Indian Sign Language, continuous sentences)

Source: [Mendeley Data, Natarajan and Elakkiya, version 1, 22 January 2021, DOI 10.17632/kcmpdxky7p.1](https://data.mendeley.com/datasets/kcmpdxky7p/1).

| Item | What is known |
|---|---|
| Licence | CC BY 4.0, as stated on the Mendeley page. Attribution is required. It does not change our INCLUDE rule: anything derived from INCLUDE stays CC BY-NC-SA 4.0, non-commercial |
| Size | One file, `ISL_CSLRT_Corpus.zip`, 8,905,822,924 bytes (8.9 GB). The file server answers with `Accept-Ranges: bytes`, so single files can be read out of the zip without fetching all of it |
| Format | A zip with no folder information in the API. The page says: 700 annotated videos, 18,863 sentence level frames (images), 1,036 word level images, and a CSV that maps the videos to the spoken sentences. Column names, video format and the folder layout are not published on the page; they are visible only inside the zip |
| Content | 100 spoken language sentences. 700 videos for 100 sentences is 7 videos per sentence, which fits 7 signers each signing each sentence once (my inference, not stated) |
| Signers | The page says 7 signers, and in the same text names two native signers from a school for the deaf in Andhra Pradesh and four student volunteers from SASTRA Deemed University, which is 6. It is not reconciled. No signer IDs are described |
| Recording | Canon DSLR on 28 December 2019, various angles, backgrounds and lighting. Frame rate, resolution and aspect ratio are not stated |
| Consent and ethics | Not stated on the page. Videos show identifiable people, some of them students |
| Annotation level | Sentence level only (the spoken sentence). There is no gloss annotation, so no sign by sign ground truth |

**Overlap with our 262 signs: cannot be measured yet.** The 100 sentences are not on the page or in any search result I could reach, and the vocabulary size is not given anywhere (another paper lists the corpus as 100 sentences with no vocabulary size). The only honest number I can give is "unknown". It can be computed cheaply once the CSV is read: run each English sentence through `text_to_gloss` and count how many glosses are INCLUDE classes, how many are in the conversation vocabulary and how many have no sign in either.

**Proposal: a continuous sentence test set, test use only, never training.**
1. Read the CSV and the zip's file list with a few byte range requests (well under 1 MB), no full download. Report the sentence list, video format, frame rate, aspect ratio and the overlap with our vocabulary. Stop and review.
2. If the overlap is useful, extract only the videos of sentences whose words are mostly covered, one zip member at a time with range requests, run Python MediaPipe Holistic with the same code path as training (`video_features`, stride 2), keep only landmark `.npy` files (the zip itself would need 8.9 GB of the 60 GB that are free, but is not needed).
3. Use it for what the corpus can really judge: segmentation (does the segmenter find a plausible number of signs per sentence), and, once a signer has written reference glosses for a subset in the Phase 3 reference format, gloss word error rate and BLEU of the recognizer plus gloss to English output. A spoken sentence alone is not a gloss reference, so recognition accuracy cannot be scored without that signer input.
4. Discipline: choose the sentences and the thresholds on a validation subset first; evaluate the final model once on the rest; add that use to the disclosure list. It is a different set of signers, camera and rooms than INCLUDE, so it measures domain shift, but its signer independence from INCLUDE is not proven either (no IDs are published for either dataset).
5. Expect a low score on most sentences: signs outside our 262 classes come out as UNRECOGNIZED by design.

Cost: reading the CSV is minutes; extracting, say, 100 to 200 videos is minutes to an hour on this machine (the INCLUDE extraction ran at roughly 100 videos per 2 to 3 minutes with 12 workers); a full pass over 700 videos is likely about 20 to 40 minutes plus the transfer of the 8.9 GB if done by one download.

## 2. WLASL (Word-Level American Sign Language)

Sources: [project repository](https://github.com/dxli94/WLASL), [paper abstract on arXiv](https://arxiv.org/abs/1910.11006), [a FiftyOne mirror on Hugging Face](https://huggingface.co/datasets/Voxel51/WLASL).

| Item | What is known |
|---|---|
| Language | American Sign Language. Not ISL: different signs, a one handed fingerspelling alphabet, and no word of the 2,000 is an INCLUDE class by construction, so labels cannot be reused |
| Licence | Computational Use of Data Agreement 1.0 (C-UDA, `C-UDA-1.0.pdf` in the repository): academic and computational use only, no commercial use, and users must read and agree to it. That is compatible with our non-commercial handling, but it is a second agreement on top of INCLUDE's, and what may be shared of a combined result must be checked against both |
| Origin of the videos | Scraped from about 20 websites including ASL education sites and YouTube (a survey table lists consent as unknown). The videos keep their original owners' rights; the dataset licence covers the annotations and the use agreement |
| Size | 21,083 videos, 2,000 glosses, 119 signers (the figures reported for the paper, found through a search summary; the abstract itself says "more than 2000 words" and "over 100 signers"). The annotation file `WLASL_v0.3.json` is 11,932,637 bytes. The repository does not state the total size of the videos |
| Format | JSON with, per video: gloss, bbox, fps (25), frame_start, frame_end, instance_id, signer_id, source, split, url, variation_id, video_id; subsets WLASL100, 300, 1000 and 2000 by top K glosses |
| How to get it | `start_kit/video_downloader.py` downloads from each `url` (yt-dlp by default); `find_missing.py` lists what failed; missing and pre processed videos can be requested from the authors through a form after agreeing to the terms, with links said to arrive within about 7 days |
| Still downloadable | **Not stated anywhere I found.** The repository says only that videos disappear when URLs expire. The one hint is a processed mirror with 11,980 samples and 5.5 GB; 11,980 of 21,083 would be 57 percent, but the mirror's page does not say whether that is all that could be fetched or a subset by design, so treat 57 percent as a guess. The real number needs a test of the URLs |

**How to find out how many are downloadable, without downloading videos:** fetch the 11.9 MB annotation file, then test a random sample of 300 URLs with an HTTP HEAD request or yt-dlp in its simulate mode and report the share that answers, per source site. Minutes of work, a few MB of traffic, no video stored. Downloading from YouTube with yt-dlp is against YouTube's terms of service even for research, so I recommend getting the videos only from the authors' own request form, which also removes the dead link problem.

**Proposal: pretraining experiment (cross language, so the outcome is genuinely uncertain).**
1. Landmarks only. Run the same Python MediaPipe pipeline (stride 2, `normalize_frame`, 225 features) over the available WLASL videos; keep the `.npy`, delete the videos. Use WLASL's own train and validation splits for pretraining.
2. Pretrain the 1D CNN (the live architecture) with a 2,000 class head on those features. A smaller subset (WLASL300 or WLASL1000) is an option if time is short.
3. Fine tune on the INCLUDE v2 training split with a fresh 262 class head; compare against the existing from scratch CNN at the same settings: seeds 0, 1, 2, validation macro-F1 per seed, and a seed by seed difference with the same 95 percent interval method as `docs/evaluation/face_results.md`. Variants: all layers fine tuned against only the head trained, and learning curves with 10, 25, 50 and 100 percent of the INCLUDE training data, because pretraining helps most when data is scarce.
4. Decisions on validation only. The INCLUDE test split is evaluated once, for the final model only, and the use is added to the disclosure list. WLASL data never enters the INCLUDE validation or test splits.
5. Expectation, honestly: the body landmark space is shared and basic hand shape and motion statistics may transfer, but the signs, the handshapes and the signing style differ, and in the face experiment (`face_results.md`) an extra input block gave no clear gain on this architecture. A null result is plausible. The experiment is cheap enough to find out.

Cost (estimates from measured INCLUDE numbers, not measured on WLASL): landmark extraction about 1 second of machine time per video with 12 workers, so about 3 to 4 hours for around 12,000 videos plus the transfer; CNN pretraining about 8 minutes on INCLUDE's 3,121 samples and 262 classes, so very roughly 30 to 60 minutes per run on 12,000 videos and 2,000 classes; 3 seeds times a few variants is an evening of training. Disk: landmarks only, well under 1 GB; the videos themselves, if fetched, are several GB (the mirror is 5.5 GB for 11,980 samples) and would be deleted after extraction.

## What I need from you before any download

1. ISL-CSLTR: may I read the CSV and the zip's file list with byte range requests (under 1 MB, no full download)?
2. WLASL: may I fetch the 11.9 MB annotation file and probe 300 URLs (headers only)? And do you want to use the authors' request form for the videos instead of scraping?
3. Which of the two experiments (ISL-CSLTR continuous test, WLASL pretraining) do you want first?
