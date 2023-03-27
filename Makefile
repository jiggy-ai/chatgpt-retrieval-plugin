# make TAG=mar25 

.PHONY: help build push all

.DEFAULT_GOAL := all

build:
	    docker build -t jiggyai/gptg-plugin:${TAG} .
push:
	    docker push jiggyai/gptg-plugin:${TAG}

all: build push
