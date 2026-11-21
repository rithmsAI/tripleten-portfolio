#include <array>
#include <charconv>
#include <cstdint>
#include <deque>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

// Deliberately small grammar: timestamp,principal,success|failure. No quoted CSV.
struct Account { std::deque<std::uint64_t> failures; bool alerted=false; };
static std::string bounded_line(std::istream& in, bool& present) {
    std::string line; char c; present=false;
    while (in.get(c)) {
        present=true;
        if (c=='\n') break;
        if (line.size()>=256) throw std::runtime_error("line exceeds 256 bytes");
        line.push_back(c);
    }
    return line;
}
static std::array<std::string,3> parse(const std::string& line) {
    const auto a=line.find(','), b=a==std::string::npos?a:line.find(',',a+1);
    if(a==std::string::npos || b==std::string::npos || line.find(',',b+1)!=std::string::npos)
        throw std::runtime_error("expected three unquoted fields");
    return {line.substr(0,a),line.substr(a+1,b-a-1),line.substr(b+1)};
}
int main() {
    try {
        std::map<std::string,Account> accounts;
        std::vector<std::pair<std::uint64_t,std::string>> alerts;
        std::uint64_t previous=0; std::size_t rows=0, bytes=0, successes=0;
        bool present; std::string line=bounded_line(std::cin,present);
        if(!present || line!="timestamp,principal,outcome") throw std::runtime_error("invalid header");
        while(true) {
            line=bounded_line(std::cin,present); if(!present) break;
            bytes+=line.size()+1;
            if(++rows>100000 || bytes>8*1024*1024) throw std::runtime_error("input limit exceeded");
            auto f=parse(line); std::uint64_t ts=0;
            auto result=std::from_chars(f[0].data(),f[0].data()+f[0].size(),ts);
            if(f[0].empty() || result.ec!=std::errc{} || result.ptr!=f[0].data()+f[0].size())
                throw std::runtime_error("invalid timestamp");
            if(rows>1 && ts<previous) throw std::runtime_error("timestamps must be ordered");
            previous=ts;
            if(f[1].empty() || f[1].size()>64) throw std::runtime_error("invalid principal length");
            for(unsigned char c:f[1]) if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
                (c>='0'&&c<='9')||c=='_'||c=='-'||c=='.')) throw std::runtime_error("invalid principal");
            if(f[2]!="success" && f[2]!="failure") throw std::runtime_error("invalid outcome");
            if(!accounts.count(f[1]) && accounts.size()>=4096) throw std::runtime_error("account limit exceeded");
            auto& account=accounts[f[1]];
            // Half-open window (ts-60, ts]; subtraction avoids unsigned overflow.
            while(!account.failures.empty() && ts-account.failures.front()>=60) account.failures.pop_front();
            if(account.failures.size()<5) account.alerted=false;
            if(f[2]=="failure") account.failures.push_back(ts); else ++successes;
            if(account.failures.size()>=5 && !account.alerted) {
                alerts.emplace_back(ts,f[1]); account.alerted=true;
            }
        }
        if(std::cin.bad()) throw std::runtime_error("input read failed");
        std::cout << "{\"rows\":" << rows << ",\"accounts\":" << accounts.size()
                  << ",\"successes\":" << successes << ",\"failures\":" << rows-successes << ",\"alerts\":[";
        for(std::size_t i=0;i<alerts.size();++i) {
            if(i) std::cout << ',';
            std::cout << "{\"timestamp\":" << alerts[i].first << ",\"principal\":\"" << alerts[i].second << "\"}";
        }
        std::cout << "]}\n";
        return std::cout?0:1;
    } catch(const std::exception& e) {
        std::cerr << "authlog: " << e.what() << '\n'; return 2;
    }
}
