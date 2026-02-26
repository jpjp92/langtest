import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, User, Bot, CreditCard, PieChart, HelpCircle, Loader2, AlertCircle, Zap, Calculator, ArrowRightLeft, Info, X, Moon, Sun } from 'lucide-react';
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
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
    { icon: <ArrowRightLeft className="w-5 h-5" />, label: '요금제 변경', text: '이용 중인 요금제를 변경하고 싶은데, 추천이나 변경 방법을 알려줄래?' },
  ];

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 overflow-hidden relative">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-white/20 px-6 py-4 flex items-center justify-between shadow-sm z-20">
        <div className="flex items-center space-x-3">
          <div className="bg-brand w-10 h-10 rounded-xl flex items-center justify-center shadow-md shadow-blue-200">
            <CreditCard className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Billing AI</h1>
            <p className="text-xs text-slate-500 font-medium">Billing Assistant</p>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          {/* Dark Mode Toggle Skeleton */}
          <button onClick={() => setIsDarkMode(!isDarkMode)} className="p-2 text-slate-400 hover:text-brand transition-colors relative group">
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            <span className="absolute right-0 top-full mt-2 w-max bg-slate-800 text-white text-xs rounded-lg px-2 py-1 opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity">
              다크 모드 준비중
            </span>
          </button>

          {/* Sidebar Toggle */}
          <button onClick={() => setIsSidebarOpen(true)} className="p-2 text-slate-600 hover:text-brand transition-colors bg-slate-100 hover:bg-blue-50 rounded-full">
            <Info className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Sidebar Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSidebarOpen(false)}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute top-0 right-0 h-full w-80 sm:w-96 bg-white/95 backdrop-blur-xl shadow-2xl z-50 border-l border-white/20 p-6 flex flex-col"
            >
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-bold text-slate-800 flex items-center">
                  <Info className="w-5 h-5 mr-3 text-brand" />
                  AI 서비스 이용 가이드
                </h2>
                <button onClick={() => setIsSidebarOpen(false)} className="p-2 text-slate-400 hover:bg-slate-100 rounded-full transition-colors active:scale-95">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-6 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-3">
                  <h3 className="text-[15px] font-semibold text-slate-800 flex items-center"><PieChart className="w-4 h-4 mr-2 text-blue-500" /> 월별 요금 상세 분석</h3>
                  <p className="text-sm text-slate-600 bg-slate-50 p-4 rounded-2xl border border-slate-100 leading-relaxed">
                    특정 월의 청구 내역을 확인하고 싶나요?<br />
                    <span className="font-medium text-brand">"2월 요금 상세 내역을 분석해줘"</span> 라고 질문하면, 초과 요금 원인(API 초과 등)을 상세히 AI가 분석해 냅니다.
                  </p>
                </div>

                <div className="space-y-3">
                  <h3 className="text-[15px] font-semibold text-slate-800 flex items-center"><Calculator className="w-4 h-4 mr-2 text-emerald-500" /> 예산 맞춤 요금제 추천</h3>
                  <p className="text-sm text-slate-600 bg-slate-50 p-4 rounded-2xl border border-slate-100 leading-relaxed">
                    갖고 있는 예산에서 최적의 효과를 내고 싶나요?<br />
                    <span className="font-medium text-brand">"연간 예산 20만원으로 요금제 섞어서 추천해줘"</span> 와 같이 문의하시면 최적의 하이브리드 조합을 구성해 드립니다.
                  </p>
                </div>

                <div className="space-y-3">
                  <h3 className="text-[15px] font-semibold text-slate-800 flex items-center"><ArrowRightLeft className="w-4 h-4 mr-2 text-indigo-500" /> 요금제 실시간/예약 변경</h3>
                  <p className="text-sm text-slate-600 bg-slate-50 p-4 rounded-2xl border border-slate-100 leading-relaxed">
                    에이전트를 통해 직접 구독 정보를 변경할 수 있어요.<br />
                    <span className="font-medium text-brand">"다음 달부터 프로 요금제로 변경 예약해줘"</span> 라고 하면 즉시 DB 상태를 업데이트합니다.
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-100">
                <p className="text-xs text-center text-slate-400 flex items-center justify-center font-medium">
                  <Zap className="w-3 h-3 mr-1 text-amber-500" /> Powered by LangGraph
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Chat Area */}
      <main
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 pt-8 pb-40 space-y-6 scroll-smooth z-0"
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
                  빌링 에이전트가 답변해 드립니다.
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
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mb-1 z-10 ${msg.role === 'user' ? 'ml-2 bg-slate-100 ring-2 ring-white/80' : 'mr-2 bg-brand text-white shadow-md ring-2 ring-white/80'
                  }`}>
                  {msg.role === 'user' ? <User className="w-5 h-5 text-slate-500" /> : <Bot className="w-5 h-5" />}
                </div>

                <div className={`px-5 py-4 rounded-2xl shadow-sm relative ${msg.role === 'user'
                  ? 'bg-gradient-to-br from-blue-600 to-brand text-white rounded-br-none shadow-blue-500/20'
                  : 'bg-white/90 backdrop-blur-sm border border-slate-100/50 text-slate-800 rounded-bl-none shadow-slate-200/50'
                  }`}>
                  <div className={`prose max-w-none text-[15px] leading-relaxed font-medium ${msg.role === 'user' ? 'prose-invert text-white' : 'prose-slate text-slate-700'}`}>
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
      <footer className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent z-10 pointer-events-none">
        <div className="max-w-4xl mx-auto pointer-events-auto">
          <form onSubmit={handleSend} className="relative flex items-end shadow-2xl shadow-brand/10 rounded-3xl bg-white/90 backdrop-blur-md border border-white p-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder="요금관련 궁금한 점을 입력하세요..."
              className="w-full bg-transparent p-4 pr-16 text-slate-800 placeholder:text-slate-400 focus:outline-none resize-none max-h-32 text-[15px] leading-relaxed"
              rows={1}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className={`absolute right-4 bottom-4 p-3 rounded-2xl transition-all duration-300 ${!input.trim() || isLoading
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-brand to-blue-500 text-white shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 active:translate-y-0'
                }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          <div className="mt-4 text-center">
            <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-widest drop-shadow-sm">
              Powered by Google Gemini ✦ LangGraph
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
