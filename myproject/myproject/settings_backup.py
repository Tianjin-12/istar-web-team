# 本地开发环境配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mvpdb',
        'USER': 'postgres',
        'PASSWORD': 'mvp123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'mvpdb',
            'USER': 'postgres',
            'PASSWORD': 'mvp123',
            'HOST': 'istar-geo.com',
            'PORT': '5432',
        }
    }