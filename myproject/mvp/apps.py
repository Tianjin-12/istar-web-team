from django.apps import AppConfig

class MvpConfig(AppConfig):
    name = 'mvp'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        # 导入dash_apps以确保Dash应用被注册
        try:
            import mvp.dash_apps
            print("MVP Dash apps 正常导入hhh")
        except ImportError as e:
            print(f"Failed to import MVP dash_apps: {e}")
            
        try:
            import mvp.cluster_viz_app
            print("ClusterVizApp 正常导入")
        except RuntimeError as e:
            if "populate() isn't reentrant" in str(e):
            # Django 启动时的正常情况，忽略
                print("ClusterVizApp: 跳过重复 django.setup()")
            else:
                raise
        except ImportError as e:
            print(f"Failed to import cluster_viz_app: {e}")

        try:
            from . import signals
            print("signals 系统正常导入hhh.")
        except ImportError as e:
            print(f"Failed to import signals: {e}")