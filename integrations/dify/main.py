from dify_plugin import DifyPluginEnv, Plugin

# A tool waits up to 90 seconds for Rollstack to answer, so a request gets a little longer than that
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
