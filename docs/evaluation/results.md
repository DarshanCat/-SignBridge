# Model comparison results

**Authors' predefined split, signer independence not verified.**

Split: predefined. Sample counts: {'train': 3121, 'val': 347, 'test': 816}.
Dataset: INCLUDE (Sridhar et al., ACM MM 2020), landmark features extracted with MediaPipe Holistic. Licence: unresolved (CC BY 4.0 per Zenodo, CC BY-NC-SA 4.0 per a third party page); treated as CC BY-NC-SA 4.0, non-commercial only, with attribution (see DATA_NOTICE.md).
Seed 0; every model uses the same split, seed, preprocessing and augmentation setting.
Training settings (identical for all three, architecture aside): epochs_max 60, batch_size 16, lr 0.001, seq_len 32, hidden 128, layers 2, heads 4, dropout 0.3, patience 10, noise_std 0.01, class_weights False, augment False, max_gap 3. Model selection and early stopping used the validation split only; the test split was evaluated once per model.

Best by validation macro-F1: **cnn**. Test numbers below come from the held-out test split.

| Model | Params | Epochs run | Val macro-F1 | Test top-1 | Test top-5 | Test macro-F1 | Test macro-P | Test macro-R |
|---|---|---|---|---|---|---|---|---|
| cnn | 343558 | 46 | 0.9039 | 0.9130 | 0.9902 | 0.9107 | 0.9307 | 0.9176 |
| bigru | 636422 | 38 | 0.7832 | 0.7929 | 0.9730 | 0.7869 | 0.8205 | 0.8072 |
| transformer | 360710 | 43 | 0.7128 | 0.7328 | 0.9596 | 0.7100 | 0.7512 | 0.7364 |

## Accuracy versus coverage (test split)

### cnn

| Threshold | Coverage | Accuracy on answered | Unrecognized |
|---|---|---|---|
| 0.00 | 1.0000 | 0.9130 | 0 |
| 0.30 | 0.9939 | 0.9174 | 5 |
| 0.50 | 0.9559 | 0.9346 | 36 |
| 0.70 | 0.8676 | 0.9548 | 108 |
| 0.80 | 0.8162 | 0.9700 | 150 |
| 0.90 | 0.7451 | 0.9770 | 208 |
| 0.95 | 0.6556 | 0.9757 | 281 |

### bigru

| Threshold | Coverage | Accuracy on answered | Unrecognized |
|---|---|---|---|
| 0.00 | 1.0000 | 0.7929 | 0 |
| 0.30 | 0.9853 | 0.8022 | 12 |
| 0.50 | 0.8885 | 0.8455 | 91 |
| 0.70 | 0.7279 | 0.9074 | 222 |
| 0.80 | 0.6446 | 0.9202 | 290 |
| 0.90 | 0.5159 | 0.9667 | 395 |
| 0.95 | 0.3983 | 0.9754 | 491 |

### transformer

| Threshold | Coverage | Accuracy on answered | Unrecognized |
|---|---|---|---|
| 0.00 | 1.0000 | 0.7328 | 0 |
| 0.30 | 0.9914 | 0.7379 | 7 |
| 0.50 | 0.9289 | 0.7665 | 58 |
| 0.70 | 0.7549 | 0.8279 | 200 |
| 0.80 | 0.6544 | 0.8652 | 282 |
| 0.90 | 0.5404 | 0.9161 | 375 |
| 0.95 | 0.4277 | 0.9542 | 467 |

## Confidence threshold used by the live recognizer

Chosen on the validation split of the best model (lowest value of [0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95] with at least 95% accuracy on answered validation samples): **0.7**; validation coverage 0.8818, validation accuracy on answered 0.9608. On the test split (the single evaluation reported above) this threshold gives coverage 0.8676 and accuracy on answered 0.9548. Signs below it are returned as UNRECOGNIZED.

## Per class accuracy (test split, best model)

| Class | Test samples | Accuracy |
|---|---|---|
| Actor | 3 | 1.000 |
| Adult | 4 | 1.000 |
| Afternoon | 1 | 0.000 |
| Alright | 4 | 1.000 |
| Animal | 4 | 1.000 |
| Artist | 3 | 1.000 |
| Attack | 3 | 1.000 |
| Author | 3 | 1.000 |
| Baby | 4 | 0.750 |
| Bag | 3 | 0.667 |
| Ball | 3 | 1.000 |
| Bank | 4 | 1.000 |
| Bathroom | 3 | 1.000 |
| Beautiful | 1 | 1.000 |
| Bed | 3 | 1.000 |
| Bedroom | 3 | 1.000 |
| Bicycle | 4 | 1.000 |
| Bill | 3 | 0.000 |
| Bird | 4 | 1.000 |
| Black | 4 | 1.000 |
| Blind | 1 | 1.000 |
| Blue | 4 | 0.250 |
| Boat | 4 | 0.500 |
| Book | 3 | 1.000 |
| Box | 3 | 1.000 |
| Boy | 4 | 1.000 |
| Brother | 4 | 0.250 |
| Brown | 4 | 1.000 |
| Bus | 4 | 1.000 |
| Camera | 3 | 1.000 |
| Car | 4 | 1.000 |
| Card | 3 | 1.000 |
| Cat | 4 | 1.000 |
| Cell phone | 3 | 0.667 |
| Chair | 3 | 0.333 |
| Child | 4 | 0.500 |
| City | 4 | 1.000 |
| Clock | 3 | 1.000 |
| Clothing | 4 | 0.750 |
| Colour | 4 | 1.000 |
| Computer | 3 | 1.000 |
| Court | 4 | 1.000 |
| Cow | 4 | 1.000 |
| Crowd | 4 | 0.750 |
| Daughter | 4 | 0.750 |
| Deaf | 1 | 1.000 |
| Death | 3 | 1.000 |
| Doctor | 3 | 1.000 |
| Dog | 4 | 1.000 |
| Door | 3 | 1.000 |
| Dream | 3 | 1.000 |
| Dress | 4 | 0.500 |
| Election | 3 | 1.000 |
| Energy | 3 | 1.000 |
| Evening | 1 | 1.000 |
| Ex. Monsoon | 3 | 1.000 |
| Exercise | 3 | 1.000 |
| Fall | 3 | 0.667 |
| Family | 3 | 1.000 |
| Fan | 3 | 0.667 |
| Father | 4 | 0.750 |
| Fish | 4 | 1.000 |
| Friday | 1 | 1.000 |
| Friend | 4 | 0.500 |
| Gift | 3 | 1.000 |
| Girl | 4 | 0.750 |
| God | 3 | 1.000 |
| Good Morning | 4 | 1.000 |
| Good afternoon | 6 | 1.000 |
| Good evening | 7 | 1.000 |
| Good night | 4 | 1.000 |
| Grandfather | 3 | 1.000 |
| Grandmother | 3 | 1.000 |
| Green | 4 | 1.000 |
| Grey | 4 | 1.000 |
| Ground | 4 | 1.000 |
| Gun | 3 | 1.000 |
| Hat | 4 | 1.000 |
| Hello | 4 | 1.000 |
| Horse | 4 | 1.000 |
| Hospital | 4 | 1.000 |
| Hour | 1 | 1.000 |
| House | 4 | 1.000 |
| How are you | 4 | 1.000 |
| Husband | 4 | 0.250 |
| I | 4 | 0.500 |
| India | 4 | 1.000 |
| Job | 3 | 1.000 |
| Key | 3 | 0.667 |
| King | 4 | 0.750 |
| Kitchen | 3 | 0.667 |
| Lamp | 3 | 1.000 |
| Laptop | 3 | 1.000 |
| Lawyer | 3 | 1.000 |
| Letter | 3 | 0.667 |
| Library | 4 | 1.000 |
| Location | 4 | 1.000 |
| Lock | 3 | 1.000 |
| Man | 4 | 1.000 |
| Manager | 3 | 1.000 |
| Market | 3 | 1.000 |
| Marriage | 3 | 1.000 |
| Mean | 2 | 1.000 |
| Medicine | 3 | 1.000 |
| Minute | 1 | 1.000 |
| Monday | 1 | 1.000 |
| Money | 3 | 1.000 |
| Month | 1 | 1.000 |
| Morning | 1 | 1.000 |
| Mother | 4 | 0.500 |
| Mouse | 4 | 1.000 |
| Neighbour | 4 | 1.000 |
| Newspaper | 3 | 1.000 |
| Nice | 1 | 1.000 |
| Night | 1 | 1.000 |
| Office | 4 | 0.750 |
| Orange | 4 | 1.000 |
| Page | 3 | 0.667 |
| Paint | 3 | 1.000 |
| Pant | 4 | 0.750 |
| Paper | 3 | 1.000 |
| Parent | 4 | 1.000 |
| Park | 4 | 1.000 |
| Patient | 3 | 1.000 |
| Peace | 3 | 1.000 |
| Pen | 3 | 0.333 |
| Pencil | 3 | 1.000 |
| Photograph | 3 | 0.667 |
| Pink | 4 | 0.500 |
| Plane | 4 | 1.000 |
| Player | 4 | 1.000 |
| Pleased | 4 | 1.000 |
| Pocket | 4 | 1.000 |
| Police | 3 | 1.000 |
| President | 4 | 1.000 |
| Price | 3 | 1.000 |
| Priest | 3 | 1.000 |
| Queen | 4 | 1.000 |
| Race (ethnicity) | 3 | 1.000 |
| Radio | 3 | 1.000 |
| Red | 4 | 0.750 |
| Religion | 3 | 1.000 |
| Reporter | 3 | 1.000 |
| Restaurant | 4 | 1.000 |
| Ring | 3 | 0.333 |
| Saturday | 1 | 1.000 |
| School | 4 | 1.000 |
| Science | 3 | 1.000 |
| Screen | 3 | 1.000 |
| Season | 3 | 1.000 |
| Second | 2 | 1.000 |
| Secretary | 3 | 1.000 |
| Shirt | 4 | 0.750 |
| Shoes | 4 | 1.000 |
| Sign | 3 | 1.000 |
| Sister | 4 | 1.000 |
| Skirt | 4 | 1.000 |
| Soap | 3 | 0.667 |
| Soldier | 3 | 1.000 |
| Son | 4 | 1.000 |
| Sport | 3 | 1.000 |
| Spring | 3 | 1.000 |
| Store or Shop | 3 | 1.000 |
| Street or Road | 4 | 1.000 |
| Student | 3 | 1.000 |
| Suit | 4 | 1.000 |
| Summer | 3 | 1.000 |
| Sunday | 1 | 0.000 |
| T-Shirt | 4 | 1.000 |
| Table | 3 | 1.000 |
| Teacher | 3 | 1.000 |
| Team | 3 | 1.000 |
| Technology | 3 | 1.000 |
| Telephone | 3 | 1.000 |
| Television | 3 | 0.333 |
| Temple | 4 | 1.000 |
| Thank you | 4 | 1.000 |
| Thursday | 1 | 1.000 |
| Time | 1 | 1.000 |
| Today | 1 | 1.000 |
| Tomorrow | 1 | 1.000 |
| Tool | 3 | 0.667 |
| Train | 4 | 1.000 |
| Train Station | 4 | 0.750 |
| Transportation | 4 | 1.000 |
| Truck | 4 | 1.000 |
| Tuesday | 1 | 1.000 |
| Ugly | 2 | 1.000 |
| University | 4 | 1.000 |
| Waiter | 3 | 1.000 |
| War | 3 | 1.000 |
| Wednesday | 1 | 1.000 |
| Week | 1 | 1.000 |
| White | 4 | 1.000 |
| Wife | 4 | 0.500 |
| Window | 3 | 1.000 |
| Winter | 3 | 1.000 |
| Woman | 4 | 1.000 |
| Year | 1 | 1.000 |
| Yellow | 4 | 0.750 |
| Yesterday | 1 | 1.000 |
| alive | 1 | 1.000 |
| bad | 4 | 0.750 |
| big large | 4 | 1.000 |
| cheap | 2 | 1.000 |
| clean | 1 | 1.000 |
| cold | 4 | 0.500 |
| cool | 4 | 1.000 |
| curved | 1 | 1.000 |
| dead | 1 | 1.000 |
| deep | 2 | 1.000 |
| dirty | 1 | 1.000 |
| dry | 4 | 1.000 |
| expensive | 2 | 0.500 |
| famous | 1 | 1.000 |
| fast | 4 | 1.000 |
| female | 2 | 1.000 |
| flat | 1 | 1.000 |
| good | 4 | 1.000 |
| happy | 4 | 1.000 |
| hard | 2 | 1.000 |
| he | 4 | 1.000 |
| healthy | 4 | 1.000 |
| heavy | 1 | 1.000 |
| high | 2 | 1.000 |
| hot | 4 | 0.750 |
| it | 4 | 1.000 |
| light | 2 | 1.000 |
| long | 4 | 1.000 |
| loose | 1 | 1.000 |
| loud | 4 | 0.750 |
| low | 1 | 1.000 |
| male | 2 | 0.500 |
| narrow | 4 | 0.750 |
| new | 4 | 1.000 |
| old | 4 | 1.000 |
| poor | 1 | 1.000 |
| quiet | 4 | 1.000 |
| rich | 2 | 1.000 |
| sad | 1 | 1.000 |
| shallow | 1 | 1.000 |
| she | 4 | 1.000 |
| short | 4 | 0.750 |
| sick | 4 | 1.000 |
| slow | 4 | 1.000 |
| small little | 4 | 1.000 |
| soft | 1 | 1.000 |
| strong | 2 | 1.000 |
| tall | 4 | 1.000 |
| they | 4 | 1.000 |
| thick | 2 | 1.000 |
| thin | 1 | 1.000 |
| tight | 1 | 1.000 |
| train ticket | 4 | 1.000 |
| warm | 4 | 1.000 |
| we | 4 | 1.000 |
| weak | 2 | 1.000 |
| wet | 4 | 1.000 |
| wide | 4 | 1.000 |
| you | 4 | 1.000 |
| you (plural) | 4 | 1.000 |
| young | 4 | 1.000 |

## Most frequent confusions (test split, best model)

| True class | Predicted as | Count |
|---|---|---|
| Brother | Sister | 3 |
| Husband | Wife | 3 |
| Blue | good | 2 |
| Boat | Fish | 2 |
| I | you | 2 |
| Mother | quiet | 2 |
| Pen | Money | 2 |
| Ring | Bill | 2 |
| Wife | Husband | 2 |
| Afternoon | Lamp | 1 |
| Baby | Monday | 1 |
| Bag | Box | 1 |
| Bill | Telephone | 1 |
| Bill | Wednesday | 1 |
| Bill | Week | 1 |

## Full confusion matrices

- cnn: [confusion_matrix_cnn.csv](confusion_matrix_cnn.csv)
- bigru: [confusion_matrix_bigru.csv](confusion_matrix_bigru.csv)
- transformer: [confusion_matrix_transformer.csv](confusion_matrix_transformer.csv)

Classes with no training sample: [].
