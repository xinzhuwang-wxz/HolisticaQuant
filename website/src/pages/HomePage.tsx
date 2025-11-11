import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, BarChart3, MessageSquare, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ApiKeySettings from '../components/ApiKeySettings';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [showApiSettings, setShowApiSettings] = useState(false);

  const scenarios = [
    {
      id: 'learning',
      title: 'Learning Studio',
      description: 'Transform abstract knowledge into actionable tasks through real-world scenarios',
      icon: Sparkles,
      color: 'from-cyan-400 to-teal-500',
      bgColor: 'bg-cyan-50/50'
    },
    {
      id: 'research',
      title: 'Research Lab',
      description: 'Generate data-driven investment reports with structured templates and real-time data',
      icon: BarChart3,
      color: 'from-emerald-400 to-green-500',
      bgColor: 'bg-emerald-50/50'
    },
    {
      id: 'qa',
      title: 'Q&A Engine',
      description: 'Get answers backed by logic, data, and verified sources',
      icon: MessageSquare,
      color: 'from-blue-400 to-indigo-500',
      bgColor: 'bg-blue-50/50'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-cyan-50/30">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-md border-b border-slate-100 z-50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-3"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="text-xl font-semibold text-slate-900">Holistica Quant</span>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="flex items-center space-x-3"
            >
              <button
                onClick={() => setShowApiSettings(true)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors flex items-center space-x-2"
              >
                <Settings className="w-4 h-4" />
                <span>API设置</span>
              </button>
              <button className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
                API Docs
              </button>
            </motion.div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="pt-32 pb-20 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <div className="mb-8">
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-teal-50 to-cyan-50 rounded-full border border-teal-200 mb-8"
              >
                <div className="w-2 h-2 bg-teal-500 rounded-full mr-3 animate-pulse"></div>
                <span className="text-sm font-medium text-teal-900">AI-Powered Investment Intelligence</span>
              </motion.div>
            </div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
              className="text-5xl lg:text-7xl font-bold text-slate-900 mb-6 leading-tight"
            >
              Virtual Quant Lab
              <span className="block bg-gradient-to-r from-teal-600 to-cyan-600 bg-clip-text text-transparent">
                for Modern Investors
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="text-xl text-slate-600 mb-12 max-w-3xl mx-auto leading-relaxed"
            >
              Transform your investment research with AI-driven insights. From learning concepts to generating reports and validating hypotheses, experience the complete research workflow in one platform.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
              className="flex flex-col sm:flex-row gap-4 justify-center"
            >
              <button 
                onClick={() => navigate('/learning')}
                className="px-8 py-4 bg-gradient-to-r from-teal-600 to-cyan-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-teal-500/25 transition-all duration-300 flex items-center space-x-2 group"
              >
                <span>Start Learning</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="px-8 py-4 bg-white text-slate-700 font-semibold rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all duration-300">
                View Documentation
              </button>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Scenarios Section */}
      <div className="py-20 px-6 lg:px-8 bg-white/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-slate-900 mb-4">
              Three Core Scenarios
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              From understanding concepts to research practice and logical validation
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-8">
            {scenarios.map((scenario, index) => (
              <motion.div
                key={scenario.id}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.6 }}
                viewport={{ once: true }}
                whileHover={{ y: -8 }}
                onClick={() => navigate(`/${scenario.id}`)}
                className={`${scenario.bgColor} p-8 rounded-2xl border border-slate-200 cursor-pointer group transition-all duration-300 hover:shadow-xl`}
              >
                <div className={`w-16 h-16 bg-gradient-to-br ${scenario.color} rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                  <scenario.icon className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-3">
                  {scenario.title}
                </h3>
                <p className="text-slate-600 mb-6 leading-relaxed">
                  {scenario.description}
                </p>
                <div className="flex items-center text-sm font-medium text-teal-600 group-hover:text-teal-700 transition-colors">
                  <span>Explore</span>
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="grid lg:grid-cols-2 gap-16 items-center"
          >
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold text-slate-900 mb-6">
                Built for the Future of Investment Research
              </h2>
              <div className="space-y-6">
                {[
                  { title: 'Real-time Data Integration', desc: 'Access live market data and financial metrics' },
                  { title: 'AI-Powered Analysis', desc: 'Advanced algorithms for pattern recognition and insights' },
                  { title: 'Collaborative Workspace', desc: 'Share research and collaborate with your team' },
                  { title: 'Export & Documentation', desc: 'Generate professional reports in multiple formats' }
                ].map((feature, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1, duration: 0.5 }}
                    viewport={{ once: true }}
                    className="flex items-start space-x-4"
                  >
                    <div className="w-2 h-2 bg-teal-500 rounded-full mt-2"></div>
                    <div>
                      <h3 className="font-semibold text-slate-900 mb-1">{feature.title}</h3>
                      <p className="text-slate-600">{feature.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="bg-gradient-to-br from-teal-100 to-cyan-100 rounded-2xl p-8 aspect-square flex items-center justify-center">
                <div className="text-center">
                  <div className="w-24 h-24 bg-white rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                    <Sparkles className="w-12 h-12 text-teal-600" />
                  </div>
                  <p className="text-slate-700 font-medium">AI-Powered Research Platform</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20 px-6 lg:px-8 bg-gradient-to-r from-teal-600 to-cyan-600">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-6">
              Ready to Transform Your Investment Research?
            </h2>
            <p className="text-xl text-teal-50 mb-8 opacity-90">
              Join the future of quantitative analysis with our AI-powered platform
            </p>
            <button 
              onClick={() => navigate('/learning')}
              className="px-8 py-4 bg-white text-teal-600 font-semibold rounded-xl hover:shadow-lg transition-all duration-300 inline-flex items-center space-x-2"
            >
              <span>Get Started</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-12 px-6 lg:px-8 bg-slate-50 border-t border-slate-200">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-semibold text-slate-900">Holistica Quant</span>
            </div>
            <div className="flex space-x-6 text-sm text-slate-600">
              <a href="#" className="hover:text-slate-900 transition-colors">Documentation</a>
              <a href="#" className="hover:text-slate-900 transition-colors">API</a>
              <a href="#" className="hover:text-slate-900 transition-colors">Support</a>
              <a href="#" className="hover:text-slate-900 transition-colors">Privacy</a>
            </div>
          </div>
        </div>
      </footer>

      {/* API密钥设置弹窗 */}
      <ApiKeySettings
        isOpen={showApiSettings}
        onClose={() => setShowApiSettings(false)}
      />
    </div>
  );
};

export default HomePage;