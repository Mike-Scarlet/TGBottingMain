
import typing

class SingleMediaAnnotateResult:
  annotate_identifier: int
  annotate_result: str
  def __init__(self) -> None:
    self.annotate_identifier = None
    self.annotate_result = None

class MediaAnnotatedResults:
  media_unique_id: str
  identifier_to_annotate_results: typing.Dict[str, SingleMediaAnnotateResult]
  def __init__(self) -> None:
    self.media_unique_id = None
    self.identifier_to_annotate_results = {}