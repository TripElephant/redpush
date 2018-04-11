FROM python:alpine3.6

ENV DESTDIR="/opt/redpush"

RUN apk update && apk add build-base
RUN mkdir -p ${DESTDIR}/redpush
RUN echo "sa"

ADD setup.py ${DESTDIR}
ADD redpush ${DESTDIR}/redpush

RUN ls -la ${DESTDIR}
RUN pip install ${DESTDIR}  -v

ENTRYPOINT ["redpush"]