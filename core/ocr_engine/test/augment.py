"""영수증 이미지 Data Augmentation 생성기"""

from pathlib import Path

from PIL import Image, ImageEnhance

SRC_DIR = Path(__file__).parent / "receipts"
AUG_DIR = Path(__file__).parent / "augmented"

# 고정 샘플 20장 (seed=42로 최초 선정 후 하드코딩)
SAMPLED_STEMS = [
    "receipt02", "receipt03", "receipt06", "receipt07", "receipt08",
    "receipt09", "receipt14", "receipt15", "receipt16", "receipt18",
    "receipt28", "receipt33", "receipt35", "receipt37", "receipt38",
    "receipt41", "receipt45", "receipt47", "receipt48", "receipt50",
]

# augmentation 조건 정의
CONDITIONS = {
    "bright_up": "밝기 +50%",
    "bright_down": "밝기 -50%",
    "low_res": "해상도 50% 축소 후 복원",
    "rotate_15": "15° 회전",
    "rotate_30": "30° 회전",
    "rotate_45": "45° 회전",
}


def augment_bright_up(img: Image.Image) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(1.5)


def augment_bright_down(img: Image.Image) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(0.5)


def augment_low_res(img: Image.Image) -> Image.Image:
    w, h = img.size
    small = img.resize((w // 2, h // 2), Image.BILINEAR)
    return small.resize((w, h), Image.BILINEAR)


def augment_rotate(img: Image.Image, angle: int) -> Image.Image:
    return img.rotate(angle, expand=True, fillcolor=(255, 255, 255))


AUGMENT_FUNCS = {
    "bright_up": augment_bright_up,
    "bright_down": augment_bright_down,
    "low_res": augment_low_res,
    "rotate_15": lambda img: augment_rotate(img, 15),
    "rotate_30": lambda img: augment_rotate(img, 30),
    "rotate_45": lambda img: augment_rotate(img, 45),
}


def generate_all():
    # 고정 20장 stem으로 이미지 경로 탐색 (png/jpg 자동 처리)
    images = []
    for stem in SAMPLED_STEMS:
        for ext in (".png", ".jpg"):
            p = SRC_DIR / (stem + ext)
            if p.exists():
                images.append(p)
                break
    print(f"샘플 이미지: {len(images)}장 (고정 20장)")
    print(f"  대상: {[img.name for img in images]}\n")

    for cond_name, cond_desc in CONDITIONS.items():
        out_dir = AUG_DIR / cond_name
        out_dir.mkdir(parents=True, exist_ok=True)

        func = AUGMENT_FUNCS[cond_name]
        for img_path in images:
            img = Image.open(img_path).convert("RGB")
            augmented = func(img)
            # 통일된 확장자(.png)로 저장
            out_name = img_path.stem + ".png"
            augmented.save(out_dir / out_name)

        print(f"  [{cond_name}] {cond_desc} → {len(images)}장 생성")

    print(f"\n총 {len(CONDITIONS)}개 조건 × {len(images)}장 = {len(CONDITIONS) * len(images)}장 생성 완료")
    print(f"저장 위치: {AUG_DIR}")


if __name__ == "__main__":
    generate_all()