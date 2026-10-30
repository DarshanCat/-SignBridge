def valid_clip(gloss: str) -> dict:
    return {
        "gloss": gloss,
        "duration": 1.0,
        "tracks": [{"bone": "upperArm_r", "keyframes": [{"t": 0, "rot": [0, 0, 0]}, {"t": 1, "rot": [-1, 0, 0]}]}],
        "source": {"author": "test", "license": "test only", "description": "synthetic test clip, not a sign"},
    }
