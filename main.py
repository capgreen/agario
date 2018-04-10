import json
from math import sin, cos, sqrt, pi
from random import random

#константы и параметры
FOOD_MASS = None
GAME_HEIGHT = None
GAME_TICKS = None
GAME_WIDTH = None
INERTION_FACTOR = None
MAX_FRAGS_CNT = None
SPEED_FACTOR = None
TICKS_TIL_FUSION = None
VIRUS_RADIUS = None
VIRUS_SPLIT_MASS = None
VISCOSITY = None
FOOD_RADIUS = 2.5
SPLIT_THRESHOLD = 120

def initParams( data ):
    global FOOD_MASS, GAME_HEIGHT, GAME_TICKS, GAME_WIDTH, INERTION_FACTOR, MAX_FRAGS_CNT, SPEED_FACTOR, TICKS_TIL_FUSION, VIRUS_RADIUS, VIRUS_SPLIT_MASS, VISCOSITY
    FOOD_MASS = data.get( 'FOOD_MASS' )
    GAME_HEIGHT = data.get( 'GAME_HEIGHT' )
    GAME_TICKS = data.get( 'GAME_TICKS' )
    GAME_WIDTH = data.get( 'GAME_WIDTH' )
    INERTION_FACTOR = data.get( 'INERTION_FACTOR' )
    MAX_FRAGS_CNT = data.get( 'MAX_FRAGS_CNT' )
    SPEED_FACTOR = data.get( 'SPEED_FACTOR' )
    TICKS_TIL_FUSION = data.get( 'TICKS_TIL_FUSION' )
    VIRUS_RADIUS = data.get( 'VIRUS_RADIUS' )
    VIRUS_SPLIT_MASS = data.get( 'VIRUS_SPLIT_MASS' )
    VISCOSITY = data.get( 'VISCOSITY' )

def makeCommand( x, y, debug ):
        command = {}
        command['X'] = x
        command['Y'] = y
        command['Debug'] = debug
        return command;
    
def distance( a, b ):
    return sqrt( ( a.X - b.X ) ** 2 + ( a.Y - b.Y ) ** 2 )

directionRange = {
            'TOP': [0.0, pi],
            'TOPRIGHT': [0.5 * pi, 0.5 * pi],
            'RIGHT': [0.5 * pi, pi],
            'BOTTOMRIGHT': [pi, 0.5 * pi],
            'BOTTOM': [pi, pi],
            'BOTTOMLEFT': [1.5 * pi, 0.5 * pi],
            'LEFT': [1.5*pi, pi],
            'TOPLEFT': [0.0, 0.5*pi]
        }

class GameObject:
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
    
    def distance( self, other ):
        return distance( self, other )

class PlayerPart( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.Id = data.get( 'Id' )
        self.R = data.get( 'R' )
        self.M = data.get( 'M' )
        
    def maxSpeed( self ):
        return SPEED_FACTOR / sqrt( self.M )    
        
class MinePart( PlayerPart ):
    def __init__( self, data ):
        super().__init__( data )
        self.VX = data.get( 'SX' )
        self.VY = data.get( 'SY' )
        # таймер слияния - может отсутствовать
        if 'TTF' in data:
            self.TTF = data.get( 'TTF' ) 
        else:
            self.TTF = 0
            
class Food( GameObject ):
    def __init__( self, data ):
        super().__init__( data )

class Ejection( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.pId = data.get( 'pId' )
    
class Virus( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.Id = data.get( 'Id' )
        self.M = data.get( 'M' )


class Strategy:
    
    def __init__( self ):
        self.mine = []
        self.direction = None
        self.food = []
        self.ejection = []
        self.virus = []
        self.player = []
        self.dangerous = []
        self.eatable = []
        self.fieldDiameter = None
        self.minSelfRadius = None
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None
        self.isSplittable = False
        self.runPoint = None #точка отступление
    
        
    def parseData( self, data ):
        mine, objects = data.get( 'Mine' ), data.get( 'Objects' )
        self.mine.clear()
        self.minSelfRadius = sqrt( GAME_HEIGHT ** 2 + GAME_WIDTH ** 2 );
        self.left = GAME_WIDTH
        self.right = 0
        self.top = GAME_HEIGHT
        self.bottom = 0
        self.isSplittable = False
        minMass = 10000.0
        for m in mine:
            self.mine.append( MinePart( m ) )
        for m in self.mine:
            self.minSelfRadius = min( self.minSelfRadius, m.R )
            self.left = min( self.left, m.X - m.R )
            self.right = max( self.right, m.X + m.R )
            self.top = min( self.top, m.Y - m.R )
            self.bottom = max( self.bottom, m.Y + m.R )
            if m.M >= SPLIT_THRESHOLD:
                self.isSplittable = True
            if m.M < minMass:
                minMass = m.M
        self.food.clear()
        self.ejection.clear()
        self.virus.clear()
        self.player.clear()
        self.dangerous.clear()
        self.eatable.clear()
        for o in objects:
            objectType = o.get( 'T' )
            if objectType == 'F':
                self.food.append( Food( o ) )
            elif objectType == 'E':
                self.ejection.append( Ejection( o ) )
            elif objectType == 'V':
                self.virus.append( Virus( o ) )
            elif objectType == 'P':
                p = PlayerPart( o )
                if minMass * 1.2 < p.M:
                    self.dangerous.append( p )
                elif minMass > p.M * 1.2:
                    self.eatable.append( p )
                else:
                    self.player.append( p )
            
    def run( self ):
        initParams( json.loads( input() ) )
        self.fieldDiameter = sqrt( GAME_WIDTH ** 2 + GAME_HEIGHT ** 2 )
        while True:
            data = json.loads( input() )
            cmd = self.on_tick( data )
            print( json.dumps(cmd) )

    def isFoodReachable( self, food ):
        effectiveRadius = self.minSelfRadius - FOOD_RADIUS / 6
        # для угла (0, 0)
        if food.X < self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X < self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        else:
            return food.X > ( FOOD_RADIUS / 6 ) and food.X < ( GAME_WIDTH - FOOD_RADIUS / 6 ) and food.Y > ( FOOD_RADIUS / 6 ) and food.Y < ( GAME_HEIGHT - FOOD_RADIUS / 6 )
        
    def get_nearest_food( self ):
        nearest = None
        minDist = self.fieldDiameter
        for food in self.food:
            if not self.isFoodReachable( food ):
                continue
            for m in self.mine:
                dist = m.distance( food )
                if dist < minDist:
                    minDist = dist
                    nearest = food
        return nearest
    
    def getBorderKey( self ):
        borderKey = ''
        if self.top <= 2:
            borderKey += 'TOP'
        elif self.bottom >= GAME_HEIGHT - 2:
            borderKey += 'BOTTOM'
        if self.left <= 2:
            borderKey += 'LEFT'
        elif self.right >= GAME_WIDTH - 2:
            borderKey += 'RIGHT'
        return borderKey
    
    def isOnBorder( self ):
        return self.top <= 0 or self.bottom >= GAME_HEIGHT or self.left <= 0 or self.right >= GAME_WIDTH
    
    def distance( self, obj ):
        distance = sqrt( GAME_WIDTH ** 2 + GAME_HEIGHT ** 2 )
        for m in self.mine:
            distance = min( distance, m.distance( obj ) )
        return distance
            
    def getNewPointToMove( self ):
        x = self.minSelfRadius + random() * ( GAME_WIDTH - self.minSelfRadius * 2 )
        y = self.minSelfRadius + random() * ( GAME_HEIGHT - self.minSelfRadius * 2 )
        point = GameObject( { 'X': x, 'Y': y } )
        while self.distance( point ) <= self.minSelfRadius:
            x = self.minSelfRadius + random() * ( GAME_WIDTH - self.minSelfRadius * 2 )
            y = self.minSelfRadius + random() * ( GAME_HEIGHT - self.minSelfRadius * 2 )
            point = GameObject( { 'X': x, 'Y': y } )
        return point
    
    def getNewDirectionToMove( self, borderKey ):
        if borderKey == '':
            return random() * 2.0 * pi
        else:
            dRange = directionRange[borderKey]
            direction = dRange[0] + random() * dRange[1]
            return direction
    
    # ищем пару опасный противник - своя часть с минимальным расстоянием
    # убегать будем по направлени, соединяющему центры этой пары
    def getRunPoint( self ):
        minDistance = 10000
        mineEnd = None
        enemyEnd = None
        for mine in self.mine:
            for enemy in self.dangerous:
                distance = mine.distance( enemy )
                if minDistance > distance:
                    mineEnd = mine
                    enemyEnd = enemy
                    minDistance = distance
        dx = mineEnd.X - enemyEnd.X
        dy = mineEnd.Y - enemyEnd.Y
        d = sqrt( dx ** 2 + dy ** 2 )
        x = mineEnd.X + ( dx * 100.0 / d )
        y = mineEnd.Y + ( dy * 100.0 / d )
        return GameObject( { 'X': x, 'Y': y } )
        
    def getAttackPoint( self ):
        minDistance = 10000
        mineEnd = None
        enemyEnd = None
        for mine in self.mine:
            for enemy in self.eatable:
                distance = mine.distance( enemy )
                if minDistance > distance:
                    mineEnd = mine
                    enemyEnd = enemy
                    minDistance = distance
        dx = enemyEnd.X - mineEnd.X
        dy = enemyEnd.Y - mineEnd.Y
        d = sqrt( dx ** 2 + dy ** 2 )
        x = mineEnd.X + ( dx * 100.0 / d )
        y = mineEnd.Y + ( dy * 100.0 / d )
        return GameObject( { 'X': x, 'Y': y } )
    
    def maxSpeed( self, obj ):
        return SPEED_FACTOR / sqrt( obj.M )
    
    def on_tick( self, data ):
        self.parseData( data )
        command = {}
        if len( self.mine ) == 0:
            command = makeCommand( 0, 0, 'game over' )
        else:
            if len( self.dangerous ) > 0:
                 #избегаем опасных соседей
                 self.runPoint = self.getRunPoint()
                 command = makeCommand( self.runPoint.X, self.runPoint.Y, 'run' )
            elif len( self.eatable ) > 0:
                 #пытаемся съесть конкурента если можем
                 attackPoint = self.getAttackPoint()
                 command = makeCommand( attackPoint.X, attackPoint.Y, 'run' )
            else:
                food = self.get_nearest_food()
                if food:
                    # пытаемся съесть еду если видно
                    command = makeCommand( food.X, food.Y, 'to food' )
                else:
                    # движемся в заданном напралении
                    borderKey = self.getBorderKey()
                    if self.direction is None or borderKey != '':
                        self.direction = self.getNewDirectionToMove( borderKey )
                    x = self.mine[0].X + cos( self.direction ) * 100
                    y = self.mine[0].Y + sin( self.direction ) * 100
                    command = makeCommand( x, y, 'by direction' )
                if self.isSplittable:
                    command['Split'] = True
        # нужно скорректировать для случая близости к границе
        return command

if __name__ == '__main__':
    s = Strategy()
    s.run()