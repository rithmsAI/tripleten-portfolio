CXX ?= g++
CXXFLAGS ?= -std=c++20 -Wall -Wextra -Werror -Wconversion -O2

authlog: authlog.cpp

test: authlog
	python3 -m unittest -v test_authlog.py

sanitize:
	$(CXX) -std=c++20 -Wall -Wextra -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer authlog.cpp -o authlog-sanitized
	AUTHLOG_BINARY=./authlog-sanitized python3 -m unittest -v test_authlog.py

clean:
	rm -f authlog authlog-sanitized

.PHONY: test sanitize clean
