#include <vector>
#include <map>

std::map<unsigned int, std::vector<float> > _lumiByRunLs;

void setLumiByLs(unsigned int run, unsigned int nlumi, float *lumi) {
    _lumiByRunLs[run].resize(nlumi);
    std::copy(lumi, lumi+nlumi, &_lumiByRunLs[run][0]);
}

float lumiByLs(int run, int ls) {
    const std::vector<float> & byls = _lumiByRunLs[run];
    if (ls >= int(byls.size())) return -1;
    return byls[ls];
}

void lumiTools() {}
