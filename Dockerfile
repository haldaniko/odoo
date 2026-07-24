FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ODOO_RC=/etc/odoo/odoo.conf

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        fonts-dejavu-core \
        fonts-font-awesome \
        fonts-freefont-ttf \
        fonts-inconsolata \
        fonts-roboto-unhinted \
        git \
        gsfonts \
        libffi-dev \
        libfreetype6-dev \
        libfribidi-dev \
        libharfbuzz-dev \
        libjpeg62-turbo-dev \
        libldap2-dev \
        liblcms2-dev \
        libopenjp2-7-dev \
        libpq-dev \
        libsasl2-dev \
        libssl-dev \
        libtiff5-dev \
        libwebp-dev \
        libxcb1-dev \
        libxml2-dev \
        libxslt1-dev \
        node-less \
        npm \
        postgresql-client \
        wkhtmltopdf \
        zlib1g-dev \
    && npm install -g rtlcss \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir /var/lib/odoo --shell /bin/bash odoo \
    && mkdir -p /etc/odoo /mnt/extra-addons /var/lib/odoo \
    && chown -R odoo:odoo /etc/odoo /mnt/extra-addons /var/lib/odoo

WORKDIR /opt/odoo

COPY requirements.txt ./
COPY docker/build-constraints.txt /tmp/build-constraints.txt
RUN pip install "pip<24.1" "setuptools==68.2.2" wheel "Cython<3" "zope.event==4.5.0" "zope.interface==5.5.2" \
    && PIP_CONSTRAINT=/tmp/build-constraints.txt pip install --no-build-isolation -r requirements.txt \
    && pip install --no-deps --force-reinstall "setuptools==68.2.2" "zope.event==4.5.0" "zope.interface==5.5.2" \
    && python -c "import pkg_resources; pkg_resources.require('zope.interface'); import zope.interface"

COPY . /opt/odoo
COPY docker/odoo.conf /etc/odoo/odoo.conf
COPY docker/odoo.prod.conf /etc/odoo/odoo.prod.conf
COPY docker/entrypoint.sh /usr/local/bin/odoo-entrypoint

RUN chmod +x /usr/local/bin/odoo-entrypoint \
    && chown -R odoo:odoo /opt/odoo /etc/odoo /mnt/extra-addons /var/lib/odoo

USER odoo

EXPOSE 8069 8072

ENTRYPOINT ["odoo-entrypoint"]
CMD ["odoo"]
