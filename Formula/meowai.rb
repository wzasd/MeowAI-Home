class Meowai < Formula
  desc "企业级多 Agent AI 协作平台"
  homepage "https://github.com/wzasd/MeowAI-Home"
  url "https://github.com/wzasd/MeowAI-Home/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "TBD"  # Fill with: shasum -a 256 <tarball>
  license "MIT"

  depends_on "python@3.11"
  depends_on "node"

  def install
    # Install Python package
    system Formula["python@3.11"].opt_bin/"python3", "-m", "pip", "install",
           "--prefix=#{prefix}", ".[dev]"

    # Install and build frontend
    cd "web" do
      system "npm", "install"
      system "npm", "run", "build"
    end

    # Copy config files
    etc.install "cat-config.json"
    etc.install ".env.example" => "meowai.env.example"
    pkgshare.install "skills", "packs"
  end

  def caveats
    <<~EOS
      MeowAI Home 已安装！

      首次使用:
        1. cp #{etc}/meowai.env.example .env
        2. meowai start

      环境检查: meowai check
      CLI 对话:  meowai chat
    EOS
  end

  service do
    run [opt_bin/"meowai", "start"]
    keep_alive true
    log_path var/"log/meowai.log"
    error_log_path var/"log/meowai.error.log"
  end

  test do
    system bin/"meowai", "--version"
  end
end
