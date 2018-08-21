# Naver Gateway Tool
Tool to help you manage your servers need to be accessed easily.

## Installing
Clone from the github
```
git clone https://github.com/SungJinYoo/naver-gw.git
cd naver-gw
git submodule init
git submodule update
```

## Migrating existing data
```
python migrate.py LEGACY_GWKIT_DIR/.known_hosts
```

## Running
```
python gwkit.py
```

It is recommend to fix your `.bashrc` file to make alias like `alias gwkit='python ~/naver-gw/'` for your convenience
