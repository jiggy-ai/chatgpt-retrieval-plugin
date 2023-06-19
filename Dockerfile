FROM python:3.11 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM ubuntu:latest

ARG DEBIAN_FRONTEND=noninteractive

ENV CFLAGS="-mno-avx512f -mno-avx512cd -mno-avx512er -mno-avx512pf -mno-avx512dq -mno-avx512bw -mno-avx512vl -mno-avx512ifma -mno-avx512vbmi"
ENV CXXFLAGS="${CFLAGS}"

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y build-essential wget curl unzip libffi-dev libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev liblzma-dev python3-openssl git libreoffice g++ ca-certificates --no-install-recommends
    

# Install Python 3.11
RUN cd /tmp && \
    wget https://www.python.org/ftp/python/3.11.4/Python-3.11.4.tar.xz && \
    tar xf Python-3.11.4.tar.xz && \
    cd Python-3.11.4 && \
    ./configure --enable-optimizations && \
    make -j8 && \
    make altinstall && \
    rm -rf /tmp/Python*

RUN ln -sf /usr/local/bin/python3.11 /usr/bin/python3
RUN ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3

# update pip
RUN pip3 install --upgrade pip


WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip3 install -r /code/requirements.txt

COPY . /code/

ENV PYTHONPATH "${PYTHONPATH}:/code"
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
