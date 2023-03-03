
import typing
from http_bots.mass_annotate_bot.media_annotate_result import *

# TODO: i18n

class PrerequisiteCheckConditionBase:
  def CheckIfConditionIsMet(self, annotate_results: MediaAnnotatedResults):
    raise NotImplementedError()

class PrerequisiteOr(PrerequisiteCheckConditionBase):
  conditions: typing.List[PrerequisiteCheckConditionBase]
  def __init__(self, *args) -> None:
    self.conditions = args
  
  def CheckIfConditionIsMet(self, annotate_results: MediaAnnotatedResults):
    # if single true, then all true
    for cond in self.conditions:
      if cond.CheckIfConditionIsMet(annotate_results):
        return True
    return False

class PrerequisiteAnd(PrerequisiteCheckConditionBase):
  conditions: typing.List[PrerequisiteCheckConditionBase]
  def __init__(self, *args) -> None:
    self.conditions = args
  
  def CheckIfConditionIsMet(self, annotate_results: MediaAnnotatedResults):
    # if single false, then all false
    for cond in self.conditions:
      if not cond.CheckIfConditionIsMet(annotate_results):
        return False
    return True

class PrerequisiteByTaskAndAnswer(PrerequisiteCheckConditionBase):
  required_task_identified_id: int
  required_answer_value: typing.Optional[typing.List[str]]
  def __init__(self, required_task_identified_id=None, required_answer_value=None) -> None:
    self.required_task_identified_id = required_task_identified_id
    # None: all answer is ok
    # otherwise must fit in the list
    self.required_answer_value = required_answer_value
    if isinstance(self.required_answer_value, str):
      self.required_answer_value = [self.required_answer_value]

  def CheckIfConditionIsMet(self, annotate_results: MediaAnnotatedResults):
    annotate_result = annotate_results.identifier_to_annotate_results.get(self.required_task_identified_id, None)
    if annotate_result is None:
      return False
    if self.required_answer_value is None:
      return True
    return annotate_result.annotate_result in self.required_answer_value

class AnnotateTasksBase:
  prerequisite: typing.List[PrerequisiteCheckConditionBase]
  annotation_question: str
  annotation_options: typing.List[str]

  identifier_id = None
  task_level = -1
  required_permission_level = 0
  """ only task level = 0 can be used as infer entry task """
  def __init__(self) -> None:
    self.prerequisite = None  # for auto infer question sequence
    self.annotation_question = ""
    self.annotation_options = []

# class GetMostBasicCategoryTask(AnnotateTasksBase):
#   identifier_id = 0
#   task_level = 0
#   def __init__(self) -> None:
#     super().__init__()
#     self.annotation_question = "brief info of roles" # 登场角色情况
#     self.annotation_options = ["all adult", "at least one underage", "garbbage media"] # ["登场人物全为成年人", "人物至少有一个非成年", "垃圾内容或无实质内容"]

class GetIsR18Task(AnnotateTasksBase):
  identifier_id = 1
  task_level = 1
