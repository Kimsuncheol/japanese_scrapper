from pydantic import BaseModel, Field


class Example(BaseModel):
    japanese: str
    reading: str = ''
    translation: str = ''


class Expression(BaseModel):
    japanese: str = Field(min_length=1)
    reading: str = ''
    translation: str = ''
    explanation: str = ''
    examples: list[Example] = Field(default_factory=list)


class Lesson(BaseModel):
    expressions: list[Expression] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)
    uncertain_text: list[str] = Field(default_factory=list)
