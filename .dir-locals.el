((nil . ((projectile-project-compilation-cmd . "zip -r ../ankiDiffSorter.ankiaddon . \
    -x \"*.pyc\" \
    -x \"__pycache__/*\" \
    -x \"*/__pycache__/*\" \
    -x \"*.git*\" \
    -x \"uv.lock\" \
    -x \"pyproject.toml\" \
    -x \"test.html\" \
    -x \"README.md\" \
    -x \"src/ankidiffsorter/*\" \
    -x \"src/mecab_controller/support/mecab.exe\" \
    -x \"src/mecab_controller/support/libmecab.dll\" \
    -x \"src/mecab_controller/support/libmecab.2.dylib\" \
    -x \"src/mecab_controller/support/mecab.mac\" \
    -x \"src/mecab_controller/support/mecab.lin\"")
         (projectile-project-test-cmd . "uv run test.py"))))
