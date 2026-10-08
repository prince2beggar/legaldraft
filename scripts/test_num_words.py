import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from packages.trust_kernel.num_to_words import (
    number_to_bangla_words,
    number_to_english_words,
    verify_numeral_word_consistency,
)

print("50000 in BN:", number_to_bangla_words(50000))
print("50000 in EN:", number_to_english_words(50000))

ok1, msg1 = verify_numeral_word_consistency(50000, "পঞ্চাশ হাজার টাকা")
print("Match BN 50000:", ok1, msg1)
assert ok1

ok2, msg2 = verify_numeral_word_consistency("৫০,০০০", "fifty thousand taka")
print("Match EN 50000 with BN numerals:", ok2, msg2)
assert ok2

ok3, msg3 = verify_numeral_word_consistency(50000, "চল্লিশ হাজার টাকা")
print("Mismatch 50000 vs 40000:", ok3, msg3)
assert not ok3

ok4, msg4 = verify_numeral_word_consistency(50000, "forty thousand")
print("Mismatch EN 50000 vs forty thousand:", ok4, msg4)
assert not ok4

print("All numeral-word consistency tests passed!")
