require 'json'

module Jekyll
  class MarketPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      markets = load_json(site, '_rawdata/markets.json')

      Jekyll.logger.info "MarketGenerator:", "#{markets.size}개 시장/상점가 페이지 생성 중..."
      total_merchants = 0
      markets.each do |m|
        next if m['slug'].to_s.strip.empty?
        site.pages << MarketPage.new(site, m)

        merchants = m['merchants'] || []
        merchants.each_with_index do |merchant, idx|
          next if merchant['slug'].to_s.strip.empty?
          siblings = pick_siblings(merchants, idx)
          site.pages << MerchantPage.new(site, merchant, m, siblings)
          total_merchants += 1
        end
      end

      Jekyll.logger.info "MarketGenerator:", "완료 (시장 #{markets.size}개 + 가맹점 #{total_merchants}개)"
    end

    private

    def pick_siblings(merchants, idx, count = 6)
      # 자기 자신을 제외하고 앞뒤로 최대 count개를 뽑음 (내부링크용, 크롤링 가능한 정적 링크)
      others = merchants.each_with_index.reject { |_, i| i == idx }.map { |m, _| m }
      others.first(count)
    end

    def load_json(site, path)
      file = File.join(site.source, path)
      return [] unless File.exist?(file)
      JSON.parse(File.read(file, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn "MarketGenerator:", "#{path} 로드 실패: #{e.message}"
      []
    end
  end

  class MarketPage < Page
    def initialize(site, m)
      @site = site
      @base = site.source
      @dir  = "market/#{m['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'market.html')
      self.data.merge!(m)
      self.data['layout']      = 'market'
      self.data['title']       = build_title(m)
      self.data['description'] = build_desc(m)
    end

    private

    def build_title(m)
      "#{m['marketName']} 온누리상품권 가맹점 #{m['merchantCount']}곳"
    end

    def build_desc(m)
      "#{m['sido']} #{m['marketName']}에서 온누리상품권을 사용할 수 있는 가맹점 #{m['merchantCount']}곳 목록. 지류형·디지털형 취급 여부를 확인하세요."[0, 155]
    end
  end

  class MerchantPage < Page
    def initialize(site, merchant, market, siblings)
      @site = site
      @base = site.source
      @dir  = "store/#{merchant['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'merchant.html')
      self.data.merge!(merchant)
      self.data['marketName']  = market['marketName']
      self.data['marketSlug']  = market['slug']
      self.data['siblings']    = siblings
      self.data['layout']      = 'merchant'
      self.data['title']       = build_title(merchant, market)
      self.data['description'] = build_desc(merchant, market)
    end

    private

    def build_title(merchant, market)
      "#{merchant['storeName']} 온누리상품권 가맹점 - #{market['marketName']}"
    end

    def build_desc(merchant, market)
      pay = []
      pay << '지류형(종이)' if merchant['paper']
      pay << '디지털형(카드·모바일)' if merchant['digital']
      pay_str = pay.empty? ? '' : "#{pay.join('·')} 상품권 사용 가능. "
      "#{market['sido']} #{market['marketName']} #{merchant['storeName']}. #{pay_str}취급품목: #{merchant['items']}"[0, 155]
    end
  end
end
