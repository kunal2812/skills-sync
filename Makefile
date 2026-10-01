.PHONY: install-local test

install-local:
	mkdir -p "$$HOME/.local/bin"
	ln -sfn "$(CURDIR)/skills-sync" "$$HOME/.local/bin/skills-sync"
	chmod +x "$(CURDIR)/skills-sync"

test:
	python3 -m unittest discover -s tests -v
