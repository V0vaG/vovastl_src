FROM python:3.10-slim

ARG VERSION
ENV VERSION=$VERSION

ARG B_NUM
ENV B_NUM=$B_NUM

ARG BRANCH
ENV BRANCH=$BRANCH

# Install system dependencies required for CadQuery
RUN apt-get update && apt-get install -y \
    gcc \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libglx-mesa0 \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/* \
    || (apt-get update && apt-get install -y \
    gcc \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/*) \
    && ln -sf /usr/lib/x86_64-linux-gnu/libOpenGL.so.0 /usr/lib/x86_64-linux-gnu/libGL.so.1 \
    && ln -sf /usr/lib/x86_64-linux-gnu/libGLX_mesa.so.0 /usr/lib/x86_64-linux-gnu/libGLX.so.0 \
    && echo '#include <stddef.h>\nvoid* glXGetProcAddressARB(const char* name) { return NULL; }\nint glXQueryVersion(void* display, int* major, int* minor) { return 0; }\nvoid* glXGetCurrentDisplay(void) { return NULL; }\nvoid* glXGetCurrentContext(void) { return NULL; }\nconst char* glXGetClientString(void* display, int name) { return NULL; }\nconst char* glXQueryExtensionsString(void* display, int screen) { return NULL; }\nint glXGetConfig(void* display, void* visual, int attrib, int* value) { return 0; }\nvoid* glXChooseVisual(void* display, int screen, int* attribList) { return NULL; }\nvoid* glXCreateContext(void* display, void* visual, void* shareList, int direct) { return NULL; }\nvoid glXDestroyContext(void* display, void* ctx) {}\nint glXMakeCurrent(void* display, void* drawable, void* ctx) { return 0; }\nvoid glXSwapBuffers(void* display, void* drawable) {}\nvoid* glXGetCurrentDrawable(void) { return NULL; }' > /tmp/glx_stub.c \
    && gcc -shared -fPIC -o /usr/lib/x86_64-linux-gnu/libGLX_stub.so /tmp/glx_stub.c \
    && rm /tmp/glx_stub.c

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--timeout", "120", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

