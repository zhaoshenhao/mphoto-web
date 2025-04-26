import logging
import settings
import cv2
import numpy as np
from typing import List
from deepface import DeepFace
from web.models import FacePhoto, BibPhoto
from pgvector.django import CosineDistance
from .tools import get_links

logger = logging.getLogger(__name__)


def prepare_image(img):
    height, width = img.shape[:2]
    if width > 800:
        scale = 800 / width
        new_width = 800
        new_height = int(height * scale)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
    return img


def get_face_representation(img):
    representations = DeepFace.represent(
        img_path=img,
        model_name=settings.FACE_MODEL,
        detector_backend=settings.FACE_DETECTOR,
        align=settings.FACE_ALIGNMENT
    )
    if not representations:
        logger.warning(f"No faces detected in image")
        return None
    embedding = None
    for rep in representations:
        confidence = rep.get('face_confidence', 0.0)
        if confidence >= settings.FACE_DETECT_CONFIDENCE:
            embedding = np.array(rep["embedding"])
            break
    if embedding is None:
        logger.warning(f"No faces with confidence >= {settings.FACE_DETECT_CONFIDENCE} in image")
        return None
    if len(embedding) != settings.EXPECTED_DIM:
        logger.error(f"Query embedding dimension mismatch: expected {settings.EXPECTED_DIM}, got {len(embedding)}")
        return None

    logger.debug(f"Input embedding dimension: {embedding.shape}")
    return embedding.tolist()


def get_embeddings(faces: List = None, ) -> List[str]:
    embeddings = []
    for face_path_or_img in faces:
        try:
            img = prepare_image(face_path_or_img)
            if img is None:
                logger.error(f"Failed to load face image: {face_path_or_img}")
                continue

            embedding = get_face_representation(img)
            if embedding:
                embeddings.append(embedding)
        except Exception as e:
            logger.error(f"Error processing face image: {str(e)}")
    return embeddings


def merge_photos(data, l):
    for i in l:
        if i['photo__gdid'] in data:
            return
        tl, dl = get_links(l['photo__storage_type'], l['photo__gdid'], l['photo__base_url'])
        data[i['photo__gdid']] = {
            'name': i['photo__name'],
            'thumb_link': tl,
            'download_link': dl,
        }


def search_face(data, embedding, event_id):
    max_distance = 1 - settings.FACE_SIMILARITY
    face_matches = FacePhoto.objects.filter(
        photo__event_id=event_id,
        confidence__gte=settings.FACE_DETECT_CONFIDENCE
    ).annotate(
        distance=CosineDistance('embedding', embedding)
    ).filter(
        distance__lt=max_distance
    ).order_by('distance')[:settings.MAX_ROWS].values(
        'photo__gdid',
        'photo__name'
    )
    l = list(face_matches)
    merge_photos(data, l)


def search_bib(data, bib_number, event_id):
    if settings.SUB_BIB:
        qs1 = BibPhoto.objects.filter(event_id=event_id, bib_number__icontains=bib_number,
                                      confidence__gt=settings.BIB_CONFIDENCE).order_by(
            'photo__name')
    else:
        qs1 = BibPhoto.objects.filter(event_id=event_id, bib_number=bib_number,
                                      confidence__gt=settings.BIB_CONFIDENCE).order_by(
            'photo__name')
    l = list(qs1[:settings.MAX_ROWS].values('photo__gdid', 'photo__name', 'photo__storage_type', 'photo__base_url'))
    merge_photos(data, l)
