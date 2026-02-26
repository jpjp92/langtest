import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, User, Bot, CreditCard, PieChart, HelpCircle, Loader2, AlertCircle, Zap, Calculator, TrendingUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';

const getApiUrl = () => {
  // 개발 환경이나 환경 변수가 설정된 경우 우선 사용
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;

  const hostname = window.location.hostname;
  // 브라우저에서 localhost로 접속하든 IP로 접속하든 해당 호스트의 8000 포트를 바라보게 함
  return `http://${hostname}:8000`;
};

const API_URL = getApiUrl();
console.log('🔗 API_URL:', API_URL);

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [threadId] = useState(`user_${Math.random().toString(36).substring(7)}`);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat`, {
        message: input,
        thread_id: threadId
      });

      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching chat:', error);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: '❌ 서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickStyles = [
    { icon: <CreditCard className="w-5 h-5" />, label: '요금제 둘러보기', text: '현재 이용 가능한 모든 요금제 종류와 특징을 알려줘' },
    { icon: <PieChart className="w-5 h-5" />, label: '월별 요금 분석', text: '지난 달 청구된 상세 요금 내역을 분석해줘' },
    { icon: <Calculator className="w-5 h-5" />, label: '맞춤 요금 설계', text: '연간 예산 20만원으로 이용할 수 있는 최적의 요금제를 추천해줘' },
    { icon: <TrendingUp className="w-5 h-5" />, label: '비용 절감 팁', text: '현재 요금에서 비용을 더 절약할 수 있는 방법이 있을까?' },
  ];

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center space-x-3">
          <div className="bg-brand w-10 h-10 rounded-xl flex items-center justify-center shadow-md shadow-blue-200">
            <CreditCard className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Billing AI</h1>
            <p className="text-xs text-slate-500 font-medium">Billing Assistant</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {/* Status Badge Removed - Non-functional */}
          <div className="relative group flex items-center">
            <button className="p-2 text-slate-400 hover:text-brand transition-colors">
              <AlertCircle className="w-5 h-5" />
            </button>
            {/* Tooltip */}
            <div className="absolute right-0 top-full mt-1 w-60 bg-slate-800 text-white text-xs rounded-xl p-3 shadow-xl opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
              <p className="font-medium mb-1 border-b border-slate-600 pb-1">💡 이용 가이드</p>
              <ul className="space-y-1 text-slate-300 leading-relaxed">
                <li>• 특정 월의 요금 상세 조회</li>
                <li>• 요금제 간의 금액 비교 및 계산</li>
                <li>• 연간/월간 예산에 맞는 요금제 추천</li>
              </ul>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-8 space-y-6 scroll-smooth"
      >
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-2xl mx-auto mt-20 text-center space-y-8"
            >
              <div className="space-y-4">
                <h2 className="text-3xl font-extrabold text-slate-800 tracking-tight">
                  무엇을 도와드릴까요?
                </h2>
                <p className="text-slate-500 text-lg">
                  요금 조회부터 개인화된 추천까지,<br />
                  똑똑한 빌링 에이전트가 답변해 드립니다.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 px-4 w-full">
                {quickStyles.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(item.text)}
                    className="flex flex-col items-center p-6 bg-white/80 backdrop-blur-sm border border-slate-100 rounded-2xl shadow-sm hover:shadow-xl hover:shadow-brand/5 hover:border-brand-light hover:-translate-y-1 transition-all duration-300 group text-center space-y-4"
                  >
                    <div className="p-4 bg-slate-50 rounded-2xl text-slate-500 group-hover:bg-blue-50 group-hover:text-brand group-hover:scale-110 transition-all duration-300">
                      {item.icon}
                    </div>
                    <span className="text-[15px] font-semibold text-slate-700 group-hover:text-slate-900 transition-colors">{item.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex max-w-[85%] sm:max-w-[75%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end space-x-2`}>
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mb-1 ${msg.role === 'user' ? 'ml-2 bg-slate-200' : 'mr-2 bg-brand text-white shadow-sm'
                  }`}>
                  {msg.role === 'user' ? <User className="w-5 h-5 text-slate-600" /> : <Bot className="w-5 h-5" />}
                </div>

                <div className={`p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                  ? 'bg-blue-50 border border-blue-100 text-slate-800 rounded-br-none'
                  : 'bg-white border border-slate-100 text-slate-800 rounded-bl-none'
                  }`}>
                  <div className="prose prose-slate max-w-none text-sm leading-relaxed font-medium">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start items-center space-x-3"
            >
              <div className="w-8 h-8 rounded-full bg-brand flex items-center justify-center shadow-sm">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white border border-slate-100 p-4 rounded-2xl flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand" />
                <span className="text-xs font-medium text-slate-500">에이전트가 생각 중입니다...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-slate-200 p-4 md:p-6 shadow-2xl z-10">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="relative flex items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder="요금관련 궁금한 점을 입력하세요."
              className="w-full bg-slate-50 border border-slate-200 rounded-2xl pl-4 pr-14 py-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-light focus:bg-white transition-all resize-none max-h-32 text-sm"
              rows={1}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className={`absolute right-2 bottom-2 p-2.5 rounded-xl transition-all ${!input.trim() || isLoading
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-brand text-white shadow-md hover:bg-brand-dark active:scale-95'
                }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          <div className="mt-3 text-center">
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">
              Powered by Google Gemini & LangGraph
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
