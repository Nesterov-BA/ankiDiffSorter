from src.get_diff import _analyze
from src.mecab_controller import MecabController

mecab = MecabController()
difficulty, formatted_sentence, all_headwords, all_unknowns = _analyze(
    sentence="時代背景[じだいはいけい]を<b> 述[の]べる</b>の",
    mature_list=["時代背景"],
    young_list=["頂けます"],
    mecab=mecab,
)
print(formatted_sentence)
print(difficulty)
print(all_headwords)
print(all_unknowns)
