/**
 * The 50 face points (of the 468 MediaPipe Holistic face mesh points) that are sent to the backend: eyebrows, eyes and mouth, in this order.
 * Must list the same numbers as backend/app/recognition/face.py FACE_INDICES (a backend test compares the two files).
 */
export const FACE_INDICES: readonly number[] = [
  // left eyebrow, right eyebrow
  70, 63, 105, 66, 107, 300, 293, 334, 296, 336,
  // left eye, right eye
  33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380,
  // mouth, outer lip
  61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185,
  // mouth, inner lip
  78, 81, 13, 311, 308, 402, 14, 178,
];

export const FULL_FACE_POINTS = 468;
