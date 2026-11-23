class VisionError(Exception):
    code: str = "vision_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class VisionDisabledError(VisionError):
    code = "vision_disabled"


class VisionImageValidationError(VisionError):
    code = "vision_image_invalid"


class VisionOcrError(VisionError):
    code = "vision_ocr_failed"


class VisionProviderError(VisionError):
    code = "vision_provider_failed"