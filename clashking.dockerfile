FROM arm64v8/python:3.11-bookworm

# Do not buffer stdout/stderr just dump it asap
ENV PYTHONUNBUFFERED 1

ARG WORKDIR=/opt/code
WORKDIR ${WORKDIR}

# This "enables" venv by adding the venv path to ${PATH}
# https://stackoverflow.com/questions/48561981/activate-python-virtualenv-in-dockerfile
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY ./requirements.txt ${WORKDIR}/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN echo 'alias ll="ls -lart --color=auto"' >> ~/.bashrc

# Entry point of dev null used for debugging
#ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "main.py"]