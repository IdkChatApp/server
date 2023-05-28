from hashlib import md5
from io import BytesIO

from PIL import Image, ImageSequence
from boto3 import client
from django.conf import settings

s3 = client(
    "s3",
    endpoint_url=getattr(settings, "S3_ENDPOINT"),
    aws_access_key_id=getattr(settings, "S3_ID"),
    aws_secret_access_key=getattr(settings, "S3_KEY"),
)

def resizeAnimImage(img: Image, size: tuple[int, int], form: str) -> bytes:
    orig_size = (img.size[0], img.size[1])

    def resize_frame(frame):
        if orig_size == size:
            return frame
        return frame.resize(size)

    frames = []
    for frame in ImageSequence.Iterator(img):
        frames.append(resize_frame(frame))
    b = BytesIO()
    frames[0].save(b, format=form, save_all=True, append_images=frames[1:], loop=0)
    return b.getvalue()

def resizeImage(image: Image, size: tuple[int, int], form: str) -> bytes:
    img = image.resize(size)
    b = BytesIO()
    img.save(b, format=form, save_all=True)
    return b.getvalue()

def imageFrames(img) -> int:
    return getattr(img, "n_frames", 1)

class S3Storage:
    @staticmethod
    def setAvatar(user_id: int, image: BytesIO, size: int) -> str:
        image_hash = md5()
        image_hash.update(image.getvalue())
        image_hash = image_hash.hexdigest()

        image = Image.open(image)
        anim = imageFrames(image) > 1
        form = "gif" if anim else "png"
        image_hash = f"a_{image_hash}" if anim else image_hash
        size = (size, size)
        func = resizeImage if not anim else resizeAnimImage
        data = func(image, size, form)
        s3.upload_fileobj(BytesIO(data), getattr(settings, "S3_BUCKET"), f"avatars/{user_id}/{image_hash}.{form}")
        return image_hash